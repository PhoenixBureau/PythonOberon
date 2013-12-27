from myhdl import intbv, concat
from util import ops, word


def make_F0(u, op, a, b, c):
  assert bool(u) == u, repr(u)
  assert ops['Mov'] <= op <= ops['Div'], repr(op)
  assert 0 <= a < 0x10, repr(a)
  assert 0 <= b < 0x10, repr(b)
  assert 0 <= c < 0x10, repr(c)
  return word(
    (u << 29) +
    (a << 24) +
    (b << 20) +
    (op << 16) +
    c
    )


for op in sorted(ops, key=ops.get):
  print '''def %s(a, b, c, u=0): return make_F0(u, %i, a, b, c)''' % (op, ops[op])

print ; print

for op in sorted(ops, key=ops.get):
  print '''def %s_imm(a, b, K, v=0, u=0): return make_F1(u, v, %i, a, b, K)''' % (op, ops[op])


##def control_unit():
##  @always(clk.posedge)
##  def next_PC():
##    IR.next = codebus.val
##    if not rst:
##      pcmux = 0
##    elif stall:
##      pcmux = PC.val
##    elif IR[32:28] == 14 and condition(): # BR
##        if u:
##          pcmux = PC.val - imm.val # wrong
##        else:
##          pcmux = C0[19:2]
##    else:
##      pcmux = PC + 1
##    PC.next = pcmux
##  return next_PC


