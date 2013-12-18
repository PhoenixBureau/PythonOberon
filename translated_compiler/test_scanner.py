import ORSX

def _e(l):
  return ''.join(
    char
    for char in l
    if char and isinstance(char, basestring)
    )


def doit():
  while True:
    ORSX.Get()
    if ORSX.sym == ORSX.null or ORSX.R_eot:
      break
    yield (
      ORSX.XWK.get(ORSX.sym, ORSX.sym),
      _e(ORSX.id_),
      ORSX.ival,
      ORSX.rval,
      ORSX.slen,
      _e(ORSX.str_),
      )
    ORSX.str_ = [None] * ORSX.stringBufSize
    ORSX.id_ = []
    ORSX.ival = 0
    ORSX.rval = 0.0
    ORSX.slen = 0



if __name__ == '__main__':
  text = open('ORSX.Mod.txt').read()
  ORSX.Init(text)
  for tok in doit():
##    print
    print tok
