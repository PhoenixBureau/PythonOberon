from myhdl import Signal, delay, always, now, Simulation, intbv, concat
from assembler import bits2signed_int, signed
from ram import sparseMemory


ibv = lambda bits, n=0: Signal(intbv(n, min=0, max=2**bits))


clk = ibv(1)
rst = ibv(1, 1)
inbus = ibv(32)
iowr = ibv(1)
outbus = ibv(32)
PC = ibv(18)
N, Z, C, OV = (ibv(1) for _ in range(4))
R = [ibv(32) for i in range(16)]
H = ibv(32)
stall1 = ibv(1)
IR = ibv(32)
pmout = ibv(32)
pcmux = ibv(12)
cond, S, sa, sb, sc = (ibv(1) for _ in range(5))
p, q, u, v, w = IR(31), IR(30), IR(29), IR(28), IR(16)
op, ira, irb, irc = IR(20, 16), IR(28, 24), IR(24, 20), IR(4, 0)
cc = IR(27, 24)
imm = IR(16, 0)
off = IR(20, 0)
##sc1, sc0 = ibv(2), ibv(2) # shift counts
ioenb = ibv(1)
(
 s1, s2, s3, t1, t2, t3,
 quotient, remainder,
 ) = (ibv(32) for _ in range(8))
product = ibv(64)
stall, stallL, stallM, stallD  = (ibv(1) for _ in range(4))


def risc_cpu():
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
##  B = R[irb].val
  B = intbv(R[irb].val)[32:]
  C0 = R[irc].val

 #C1 = ~q ? C0 : {{16{v}}, imm};
  # except it seems ~~q...:
  C1 = concat(*([v] * 16 + [imm])) if q else C0

  ioenb.next = (pmout[20:6] == 0b11111111111111);
  outbus.next = A

##  sc0 = C1[1:0];
##  sc1 = C1[3:2];

  if MOV:
   #  (q ? (~u ? {{16{v}}, imm} : {imm, 16'b0}) :
    if q:
      if not u:
        res = concat(*([v] * 16 + [imm]))
      else:
        res = concat(imm, intbv(0)[16:])
    else:
     #  (~u ? C0 : ... )) :
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
    res = s3.val
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
    print B, C1, x
    res = signed(x, 32)
  elif SUB:
    res = B - C1 - (u & C)
    print B, C1, res
    res = signed(res, 32)
  elif MUL:
    res = product[32:0]
  elif DIV:
    res = quotient.val
  else:
    res = 0

  aluRes = intbv(res)

  # The control unit

  nxpc = PC + 1

  if (LDR & (not ioenb)):
    regmux = dmout
  elif (LDR & ioenb):
    regmux = inbus
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

  regwr = (not p) & (not stall) | (LDR & stall1)| (BR & cond & v)

  IR.next = pmout.val

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

  PC.next = pcmux;

  sa = aluRes[31];
  sb = B[31];
  sc = C1[31] ^ SUB;

  stall.next = stallL | stallM | stallD;
  stallL.next = LDR & (not stall1);

  stall1.next = stallL;
  R[ira0].next = regmux if regwr else A
  N.next = regmux[31] if regwr else N
  Z.next = (regmux[31:0] == 0) if regwr else Z
  C.next = aluRes[32] if (ADD|SUB) else C
  OV.next = (sa & (not sb) & (not sc) | (not sa) & sb & sc) if (ADD|SUB) else OV
  H.next = product[63:32] if MUL else remainder if DIV else H


def ClkDriver(clk, period=10):
  halfPeriod = delay(period / 2)
  @always(halfPeriod)
  def driveClk():
    clk.next = not clk
  return driveClk


def iii(clk):
  @always(clk.negedge)
  def jjj():
    print '0x%04x: 0x%08x -> 0x%08x' % (
      PC,
      memory[int(PC)],
      IR,
      )
    for i, reg in enumerate(R):
      if reg:
        print 'R[0x%02x] == 0x%08x == %i' % (i, reg, reg)
    print
  return jjj


if __name__ == '__main__':
  from collections import defaultdict
  from assembler import Mov_imm, Add, Lsl_imm, T_link

  memory = {} # defaultdict(int)
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

  sim = Simulation(
    ClkDriver(clk),
    sparseMemory(memory, pmout, outbus, PC, iowr, stall1, clk),
    always(clk.posedge)(risc_cpu),
    iii(clk),
    )
  print "PC    : RAM[PC]     ->  IR"
  print "0x%04x: 0x%08x" % (PC, memory[0])
  sim.run(120)
