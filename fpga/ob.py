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
memory[0] = ibv(32, 23)
RAM = sparseMemory(memory, codebus, outbus, adr, wr, stall, clk)


IR = ibv(32)
p, q, u, v, w = IR(31), IR(30), IR(29), IR(28), IR(16)
op, ira, irb, irc = IR(20, 16), IR(28, 24), IR(24, 20), IR(4, 0)
imm = IR(16, 0)

PC = ibv(18)

(A, B, C0, C1, regmux,
 s3, t3, quotinent, fsum, fprod, fquot) = (Signal(intbv(0, min=0, max=2**32))
                                           for _ in range(11))
aluRes = ibv(33)
product = ibv(64)
R = [ibv(32, i) for i in range(16)]
N, Z, C, OV = (Signal(0) for _ in range(4))


def ClkDriver(clk):
  halfPeriod = delay(10)
  @always(halfPeriod)
  def driveClk():
    clk.next = not clk
  return driveClk


def HelloWorld(clk):

  @always(clk.posedge)
  def sayHello():
    IR.next = IR.val + 1
    A.next = R[ira].val
    B.next = R[irc].val
    C0.next = R[irc].val
    C1.next = concat(*([v] * 16 + [imm])) if q else R[irc].val
##assign C1 = q ? {{16{v}}, imm} : C0;

  return sayHello


def control_unit(clk):
  @always(clk.posedge)
  def next_PC():
#    IR.next = codebus.val
    if not rst:
      pcmux = 0
    elif stall:
      pcmux = PC
##(BR & cond & u) ? off + nxpc :
##(BR & cond & ~u) ? C0[19:2] :
    else:
      pcmux = PC + 1
    PC.next = pcmux
  return next_PC

def iii(clk):
  @always(clk.negedge)
  def jjj():
    print "%s Hello World!" % now(), PC
    print bin(IR)[2:], bin(irc)[2:], A, B
  return jjj


clkdriver_inst = ClkDriver(clk)
hello_inst = HelloWorld(clk)
sim = Simulation(RAM, clkdriver_inst, hello_inst, iii(clk), control_unit(clk))
sim.run(150)
