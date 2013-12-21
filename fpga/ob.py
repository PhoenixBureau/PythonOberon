from collections import defaultdict
from myhdl import Signal, delay, always, now, Simulation, intbv, concat
from ram import sparseMemory


ibv = lambda bits, n=0: Signal(intbv(n, min=0, max=2**bits))


clk = Signal(0)
rst = Signal(1)
stall = Signal(0)
rd = Signal(0)
wr = Signal(0)
ben = Signal(0)

inbus = ibv(32)
outbus = ibv(32)
codebus = ibv(32)
adr = ibv(20)


memory = defaultdict(int)
memory[5] = ibv(32, 0b11100111000000000000000000000011)


IR = ibv(32)
p, q, u, v, w = IR(31), IR(30), IR(29), IR(28), IR(16)
op, ira, irb, irc = IR(20, 16), IR(28, 24), IR(24, 20), IR(4, 0)
imm = IR(16, 0)

PC = ibv(18)

(A, B, C0, C1, regmux,
 s3, t3, quotinent, fsum, fprod, fquot) = (ibv(32) for _ in range(11))

aluRes = ibv(33)
product = ibv(64)
R = [ibv(32, 9) for i in range(16)]
N, Z, C, OV = (Signal(0) for _ in range(4))



def ClkDriver(clk, period=10):
  halfPeriod = delay(period / 2)
  @always(halfPeriod)
  def driveClk():
    clk.next = not clk
  return driveClk


def condition():
  cc = ira
  S = N ^ OV
  return (
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


def ALU(op, q, u, v, imm, irc, N, Z, C, OV, C0, aluRes):
##  MOV ?
  if op == Mov:
##  (q ? (~u ? {{16{v}}, imm} : {imm, 16'b0}) :
    if q:
      if ~u:
        res = concat(*([v] * 16 + [imm]))
      else:
        res = concat(imm, *([intbv(0)] * 16))
    else:
##  (~u ? C0 : ... )) :
      if ~u:
        res = C0.val
      else:
# ... (~irc[0] ? H : {N, Z, C, OV, 20'b0, 8'b01010000})
        if ~irc[0]:
          res = H # wtf is H?
        else:
          res = concat(
            N, Z, C, OV,
            intbv(0)[20:],
            intbv(0b01010000),
            )
  aluRes.next = res


def thinker():

  @always(clk.posedge)
  def think():
    A.next = R[ira].val
    B.next = R[irb].val
    C0.next = R[irc].val
    C1.next = concat(*([v] * 16 + [imm])) if q else R[irc].val
    adr.next = PC.val # for now..
##assign C1 = q ? {{16{v}}, imm} : C0;
    ALU(op, q, u, v, imm, irc, N, Z, C, OV, C0, aluRes)
    R[ira].next = aluRes.next

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
  sparseMemory(memory, codebus, outbus, adr, wr, stall, clk),
  thinker(),
  control_unit(),
  iii(clk),
  )
print "                      IR,                                codebus, adr, PC"
sim.run(250)
