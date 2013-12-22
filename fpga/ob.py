from collections import defaultdict
from myhdl import Signal, delay, always, now, Simulation, intbv, concat
from ram import sparseMemory


ibv = lambda bits, n=0: Signal(intbv(n, min=0, max=2**bits))


clk = ibv(1)
rst = ibv(1)
inbus = ibv(32)
ioadr = ibv(6)
iord = ibv(1)
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
nxpc = ibv(12)
cond, S, sa, sb, sc = (ibv(1) for _ in range(5))


p, q, u, v, w = IR(31), IR(30), IR(29), IR(28), IR(16)
op, ira, ira0, irb, irc = (IR(20, 16), IR(28, 24), ibv(4),
                           IR(24, 20), IR(4, 0))
cc = IR(27, 24)
imm = IR(16, 0)
off = IR(20, 0)

ccwr, regwr = ibv(1), ibv(1)
dmadr = ibv(14)
dmwr, ioenb = ibv(1), ibv(1)
dmin = ibv(32)
dmout = ibv(32)
sc1, sc0 = ibv(2), ibv(2) # shift counts


(A, B, C0, C1, regmux,
 s1, s2, s3, t1, t2, t3,
 quotient, remainder,
 ) = (ibv(32) for _ in range(13))
#aluRes = ibv(33)
product = ibv(64)
stall, stallL, stallM, stallD  = (ibv(1) for _ in range(4))


##fsum, fprod, fquot
ben = Signal(0)
codebus = ibv(32)
adr = ibv(20)
memory = defaultdict(int)
memory[5] = ibv(32, 0b11100111000000000000000000000011)


def assign():
  IR.next = pmout.val
  MOV = ~p & (op == 0);
  LSL = ~p & (op == 1);
  ASR = ~p & (op == 2);
  ROR = ~p & (op == 3);
  AND = ~p & (op == 4);
  ANN = ~p & (op == 5);
  IOR = ~p & (op == 6);
  XOR = ~p & (op == 7);
  ADD = ~p & (op == 8);
  SUB = ~p & (op == 9);
  MUL = ~p & (op == 10);
  DIV = ~p & (op == 11);

  LDR = p & ~q & ~u;
  STR = p & ~q & u;
  BR  = p & q;

  A.next = R[ira0].val
  B.next = R[irb].val
  C0.next = R[irc].val

  # Arithmetic-logical unit (ALU)
  ira0.next = 15 if BR else ira
 #C1 = ~q ? C0 : {{16{v}}, imm};
  C1.next = concat(*([v] * 16 + [imm])) if ~q else C0.val

  dmadr.next = B[13:0] + off[13:0];
  dmwr.next = STR & ~stall;
  dmin.next = A.val;

  ioenb.next = (dmadr[13:6] == 0b11111111);
  iowr.next = STR & ioenb;
  iord.next = LDR & ioenb;
  ioadr.next = dmadr[5:0];
  outbus.next = A.val;

  sc0 = C1[1:0];
  sc1 = C1[3:2];

 #  MOV ?
  if MOV:
   #  (q ? (~u ? {{16{v}}, imm} : {imm, 16'b0}) :
    if q:
      if ~u:
        res = concat(*([v] * 16 + [imm]))
      else:
        res = concat(imm, *([intbv(0)] * 16))
    else:
     #  (~u ? C0 : ... )) :
      if ~u:
        res = C0.val
      else:
     #... (~irc[0] ? H : {N, Z, C, OV, 20'b0, 8'b01010000})
        if ~irc[0]:
          res = H.val
        else:
          res = concat(
            N, Z, C, OV,
            intbv(0)[20:],
            intbv(0b01010000),
            )
  elif LSL:
    res = t3.val
  elif ASR or ROR:
    res = t3.val
  elif AND:
    res = B & C1
  elif ANN:
    res = B & ~C1
  elif IOR:
    res = B | C1
  elif XOR:
    res = B ^ C1
  elif ADD:
    res = B + C1 + (u & C)
  elif SUB:
    res = B - C1 - (u & C)
  elif MUL:
    res = product[32:0]
  elif DIV:
    res = quotient.val
  else:
    res = 0

  aluRes = res

  if (LDR & ~ioenb):
    regmux = dmout
  elif (LDR & ioenb):
    regmux = inbus
  elif (BR & v):
    regmux = concat(intbv(0)[18:], nxpc, intbv(0)[2:])
    # {18'b0, nxpc, 2'b0}
  else:
    regmux = aluRes

  S = N ^ OV
  nxpc = PC + 1
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

  regwr = ~p & ~stall | (LDR & stall1)| (BR & cond & v)

  if ~rst:
    pcmux = 0
  elif stall:
    pcmux = PC
  elif BR & cond & u:
    pcmux = off[11:0] + nxpc
  elif (BR & cond & ~u):
    pcmux = C0[13:2]
  elif (BR & cond & ~u & IR[5]):
    pcmux = concat(intbv(0)[14:], irc)
    # {14'b0, irc}
  else:
    pcmux = nxpc

  sa = aluRes[31];
  sb = B[31];
  sc = C1[31] ^ SUB;

  stall.next = stallL | stallM | stallD;
  stallL.next = LDR & ~stall1;

  PC.next = pcmux;
  stall1.next = stallL;
  R[ira0].next = regmux if regwr else A
  N.next = regmux[31] if regwr else N
  Z.next = (regmux[31:0] == 0) if regwr else Z
  C.next = aluRes[32] if (ADD|SUB) else C
  OV.next = (sa & ~sb & ~sc | ~sa & sb & sc) if (ADD|SUB) else OV
  H.next = product[63:32] if MUL else remainder if DIV else H


def ClkDriver(clk, period=10):
  halfPeriod = delay(period / 2)
  @always(halfPeriod)
  def driveClk():
    clk.next = not clk
  return driveClk


def control_unit():
  @always(clk.posedge)
  def next_PC():
    IR.next = codebus.val
    if not rst:
      pcmux = 0
    elif stall:
      pcmux = PC.val
    elif IR[32:28] == 14 and condition(): # BR
        if u:
          pcmux = PC.val - imm.val # wrong
        else:
          pcmux = C0[19:2]
    else:
      pcmux = PC + 1
    PC.next = pcmux
  return next_PC


Mov = 0; Lsl = 1; Asr = 2; Ror= 3; And = 4; Ann = 5; Ior = 6; Xor = 7;
Add = 8; Sub = 9; Cmp = 9; Mul = 10; Div = 11;
Fad = 12; Fsb = 13; Fml = 14; Fdv = 15;
Ldr = 8; Str = 10;




def thinker():

  @always(clk.posedge)
  def think():
    assign()
##    adr.next = PC.val # for now..
####assign C1 = q ? {{16{v}}, imm} : C0;
##    ALU(op, q, u, v, imm, irc, N, Z, C, OV, C0, aluRes)
##    R[ira].next = aluRes.next

  return think


def iii(clk):
  @always(clk.negedge)
  def jjj():
    print '%32s %32s %s %s' % (
      bin(IR)[2:], bin(codebus)[2:], adr, PC
      )
  return jjj


sim = Simulation(
  ClkDriver(clk),
  sparseMemory(memory, pmout, outbus, adr, iowr, stall1, clk),
  thinker(),
  iii(clk),
  )
print "                      IR,                                codebus, adr, PC"
sim.run(250)
