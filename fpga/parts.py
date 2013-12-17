from myhdl import Signal, delay, always, now, Simulation, intbv, concat


ibv = lambda bits, n=0: Signal(intbv(n, min=0, max=2**bits))


def ClkDriver(clk, period=10):
  halfPeriod = delay(period / 2)
  @always(halfPeriod)
  def driveClk():
    clk.next = not clk
  return driveClk


class condition:
  def __init__(self, cc, ir27, N, Z, C, OV):
    self.args = cc, ir27, N, Z, C, OV
  def __call__(self):
    cc, ir27, N, Z, C, OV = self.args
    S = N ^ OV
    return (
      ir27 ^
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


def control_unit(clk, IR, codebus, rst, stall, PC, cond, off, u, C0):
  @always(clk.posedge)
  def next_PC():
    IR.next = codebus.val
    if not rst:
      pcmux = 0
    elif stall:
      pcmux = PC.val
    elif IR[32:28] == 14 and cond(): # BR
        if u:
          pcmux = PC.val - off.val # wrong
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


def thinker(clk, IR, A, B, C0, C1, v, imm, q, R,
            ira, irb, irc, adr, PC,
            N, Z, C, OV, op, u, aluRes
            ):

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


