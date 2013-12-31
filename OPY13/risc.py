from myhdl import Signal, delay, always, now, Simulation, intbv, concat
from util import ibv, bits2signed_int, signed
from disassembler import dis
from ram import sparseMemory


_RAM = None # Used for debugging, set to actual ram dict!


def risc_cpu(clk, rst, inbus, adr, iowr, stall1, outbus):

  PC = adr
  pcbuffer = Signal(intbv(0)[len(adr):])

  IR = pmout = inbus
  p, q, u, v, w = IR(31), IR(30), IR(29), IR(28), IR(16)
  op, ira, irb, irc = IR(20, 16), IR(28, 24), IR(24, 20), IR(4, 0)
  cc = IR(27, 24)
  imm = IR(16, 0)
  off = IR(20, 0)

  N, Z, C, OV = (ibv(1) for _ in range(4))
  R = [ibv(32) for i in range(16)]
  H = ibv(32)

  stallL = [0]

  @always(clk.posedge)
  def cycle():

    kw = locals().copy()
    kw.update(globals())
    debug_it(kw)

    MOV = (not p) & (op == 0)
    LSL = (not p) & (op == 1)
    ASR = (not p) & (op == 2)
    ROR = (not p) & (op == 3)
    AND = (not p) & (op == 4)
    ANN = (not p) & (op == 5)
    IOR = (not p) & (op == 6)
    XOR = (not p) & (op == 7)
    ADD = (not p) & (op == 8)
    SUB = (not p) & (op == 9)
    MUL = (not p) & (op == 10)
    DIV = (not p) & (op == 11)

    LDR = p & (not q) & (not u)
    STR = p & (not q) & u
    BR  = p & q

    ira0 = 15 if BR else ira

    # Arithmetic-logical unit (ALU)

    A = R[ira0].val
    B = R[irb].val
    C0 = R[irc].val

    # C1 = ~q ? C0 : {{16{v}}, imm};
    # except it seems ~~q...
    bits = 16 * [v] + [imm]
    C1 = concat(*bits) if q else C0

    ##  ioenb.next = (pmout[20:6] == 0b11111111111111);
    outbus.next = A

    ##  sc0 = C1[1:0];
    ##  sc1 = C1[3:2];

    if MOV:
      # (q ? (~u ? {{16{v}}, imm} : {imm, 16'b0}) :
      if q:
        res = C1 if not u else concat(imm, intbv(0)[16:])
      else:
        # (~u ? C0 : ... )) :
        if not u:
          res = C0
        else:
          # ... (~irc[0] ? H : {N, Z, C, OV, 20'b0, 8'b01010000})
          if not irc[0]:
            res = H.val
          else:
            res = concat(
              N, Z, C, OV,
              intbv(0)[20:],
              intbv(0b01010000),
              )
    elif LSL:
      res = B << C1
    elif ASR or ROR:
      res = B >> C1 # FIXME not quite right is it?
    elif AND:
      res = B & C1
    elif ANN:
      res = B & ~C1
    elif IOR:
      res = B | C1
    elif XOR:
      res = B ^ C1
    elif ADD:
      x = B + C1 + (u & C)
      res = signed(x, 32)
    elif SUB:
      res = B - C1 - (u & C)
      res = signed(res, 32)
    elif MUL:
      product = intbv(B * C1)
      res = product[32:0]
    elif DIV:
      res = intbv(B / C1)
      remainder = B % C1
    else:
      res = 0

    aluRes = res if isinstance(res, intbv) else intbv(res)[32:0]

    # The control unit

    nxpc = PC + 1

    if LDR:
      regmux = pmout.val
    elif (BR & v):
      regmux = concat(nxpc, intbv(0)[2:])
      # {18'b0, nxpc, 2'b0}
    else:
      regmux = aluRes

    S = N ^ OV
    cond = (
      IR[27] ^
      ((cc == 0) & N |
       (cc == 1) & Z |
       (cc == 2) & C |
       (cc == 3) & OV |
       (cc == 4) & (C|Z) |
       (cc == 5) & S |
       (cc == 6) & (S|Z) |
       (cc == 7)
       )
      )

    stall = stallL[0]
    stallL[0] = (LDR|STR) and not stall1
    stall1.next = stallL[0]
    print now(), 'stall:', stall, 'stallL:', stallL, 'stall1:', stall1, 'LDR' if LDR else 'STR' if STR else ''
    print
    iowr.next = STR and not stall1

    regwr = (not p) & (not stall) | (LDR and stall1) | (BR & cond & v)

    if not rst:
      pcmux = 0
    elif stall:
      pcmux = PC.val
    elif BR & cond & u:
      pcmux = bits2signed_int(off[12:0]) + nxpc
    elif (BR & cond & (not u)):
      pcmux = C0[20:2]
    elif (BR & cond & (not u) & IR[5]):
      pcmux = concat(intbv(0)[14:], irc)
      # {14'b0, irc}
    else:
      pcmux = nxpc

    if STR | LDR:
      if not stall:
        # Stash the current pcmux
        pcbuffer.next = pcmux
      else:
        # Restore that saved PC
        pcmux = pcbuffer

    PC.next = intbv(B + off)[len(PC):] if stallL[0] else pcmux

    sa = aluRes[31]
    sb = B[31]
    sc = C1[31] ^ SUB

    R[ira0].next = regmux if regwr else A
    N.next = regmux[31] if regwr else N
    Z.next = (regmux[31:0] == 0) if regwr else Z
    C.next = aluRes[32] if (ADD|SUB) else C
    OV.next = (sa & (not sb) & (not sc) | (not sa) & sb & sc) if (ADD|SUB) else OV
    H.next = product[64:32] if MUL else remainder if DIV else H

  return cycle


def ClkDriver(clk, period=10):
  halfPeriod = delay(period / 2)
  @always(halfPeriod)
  def driveClk():
    clk.next = not clk
  return driveClk


def debug_it(kw):
  global _RAM
  kw['dis'] = dis(int(kw['IR']))
  R = kw['R']

  print 'Fetch 0x%(PC)04x' % kw, dis(int(_RAM[int(kw['PC'])]))
  print 'Execute: 0x%(IR)08x = %(dis)s' % kw

  if kw['iowr']:
    print 'Storing', '[0x%(PC)04x] <- 0x%(outbus)08x' % kw
    print
    return
    
  for i in range(0, 16, 2):
    reg0, reg1 = R[i], R[i + 1]
    print 'R%-2i = 0x%-8x' % (i + 1, reg1),
    print 'R%-2i = 0x%-8x' % (i, reg0)
  print
  for i in range(0, 16):
    print '[%x]: 0x%x' % (i, _RAM[i])
  print


if __name__ == '__main__':
  clk = ibv(1)
  rst = ibv(1, 1)
  inbus = ibv(32)
  outbus = ibv(32)
  adr = ibv(18)
  iowr = ibv(1)
  stall1 = ibv(1)

  ##pmout = ibv(32)
  ##pcmux = ibv(12)
  ##cond, S, sa, sb, sc = (ibv(1) for _ in range(5))

  ##sc1, sc0 = ibv(2), ibv(2) # shift counts
##  ioenb = ibv(1)
##  (
##   s1, s2, s3, t1, t2, t3,
##   quotient, remainder,
##   ) = (ibv(32) for _ in range(8))
##  product = ibv(64)

  from collections import defaultdict
  from assembler import Mov_imm, Add, Lsl_imm, T_link

  memory = defaultdict(int)
  memory.update({
    0: Mov_imm(8, 1),
    1: Mov_imm(1, 1),
    2: Add(1, 1, 8),
    3: Lsl_imm(1, 1, 2),
    4: T_link(1),
    5: 0,
    6: 0,
    9: 0,
    })

  global _RAM
  _RAM = memory

  sim = Simulation(
    ClkDriver(clk),
    sparseMemory(memory, inbus, outbus, adr, iowr, clk),
    risc_cpu(clk, rst, inbus, adr, iowr, stall1, outbus),
    )
  sim.run(120)
