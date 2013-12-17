

RESERVED_WORDS = set('''\
  ARRAY RECORD
  '''.split())


BASE_TYPES = set('''\
  INTEGER
  '''.split())


def realize(s, e, sc):
  f = float("".join(s)+'.'+"".join(e))
  if sc is not None:
    f *= 10**sc
  return f


class ObAST(object):
  def __init__(self, *stuff):
    self.value = list(stuff)
  def __repr__(self):
    return '%s(%s)' % (self.__class__.__name__, self.value)


class Qualident(ObAST):
  def __init__(self, a, b):
    self.a, self.b = a, b
    self.value = b if a is None else (a + '.' + b)


class IdentDef(ObAST):
  def __init__(self, i, public):
    self.i, self.public = i, public
    self.value = i if public is None else (i + '*')


class Const(ObAST): pass
class Typ(ObAST): pass
class Array(ObAST): pass
