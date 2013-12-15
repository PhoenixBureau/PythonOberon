from collections import defaultdict
from myhdl import Signal, delay, always, now, Simulation, intbv, concat
from ram import sparseMemory
from parts import ClkDriver, control_unit, thinker


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


def iii(clk):
  @always(clk.negedge)
  def jjj():
    print bin(IR)[2:], bin(irc)[2:], A, B, now(), PC
  return jjj


sim = Simulation(
  ClkDriver(clk),
  sparseMemory(memory, codebus, outbus, adr, wr, stall, clk),
  thinker(clk, IR, A, B, C0, C1, v, imm, q, R, ira, irb, irc),
  control_unit(clk, IR, codebus, rst, stall, PC),
  iii(clk),
  )
sim.run(150)
