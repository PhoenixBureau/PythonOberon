from myhdl import Signal, delay, always, now, Simulation, intbv, concat


ibv = lambda bits, n=0: Signal(intbv(n, min=0, max=2**bits))


def ClkDriver(clk, period=10):
  halfPeriod = delay(period / 2)
  @always(halfPeriod)
  def driveClk():
    clk.next = not clk
  return driveClk


def control_unit(clk, IR, codebus, rst, stall, PC):
  @always(clk.posedge)
  def next_PC():
    IR.next = codebus.val
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


def thinker(clk, IR, A, B, C0, C1, v, imm, q, R,
               ira, irb, irc):

  @always(clk.posedge)
  def think():
    A.next = R[ira].val
    B.next = R[irb].val
    C0.next = R[irc].val
    C1.next = concat(*([v] * 16 + [imm])) if q else R[irc].val
##assign C1 = q ? {{16{v}}, imm} : C0;

  return think


