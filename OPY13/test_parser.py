import sys
import ORPX, ORSX, ORBX, ORGX, disassembler

#fn = '/home/sforman/Desktop/Oberon/PO/Kernel.Mod.txt'
fn = 'Pattern2.Mod.txt'

text = open(fn).read()
try:
  ORPX.Compile(text)
except:
  print >> sys.stderr
  print >> sys.stderr, '-' * 40
  print >> sys.stderr, 'Error near line %i, character %i' % (
    text[:ORSX._pos].count('\n') + 1,
    ORSX._pos,
    )
  print >> sys.stderr, text[ORSX._pos - 20:ORSX._pos],
  print >> sys.stderr, '^^Err^^',
  print >> sys.stderr, text[ORSX._pos:ORSX._pos + 20]
  print >> sys.stderr, '-' * 40
  raise

for k in sorted(ORGX.code):
  I = ORGX.code[k]
  s = bin(I)[2:]
  s = '0' * (32 - len(s)) + s
  print s, '%08x' % (I,), disassembler.dis(I)
