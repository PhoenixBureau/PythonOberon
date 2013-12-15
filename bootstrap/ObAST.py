

RESERVED_WORDS = set('''\
  ARRAY
  '''.split())


BASE_TYPES = set('''\
  INTEGER
  '''.split())


def realize(s, e, sc):
  f = float("".join(s)+'.'+"".join(e))
  if sc is not None:
    f *= 10**sc
  return f


class Qualident:
  def __init__(self, a, b):
    self.a, self.b = a, b
    self.value = b if a is None else (a + '.' + b)
  def __repr__(self):
    return 'Qualident(' + self.value + ')'


class IdentDef:
  def __init__(self, i, public):
    self.i, self.public = i, public
    self.value = i if public is None else (i + '*')
  def __repr__(self):
    return 'IdentDef(' + self.value + ')'


class Const:
  def __init__(self, i, e):
    self.i, self.e = i, e
    self.value = [i, e]
  def __repr__(self):
    return 'Const(%s)' % (self.value,)


class Typ:
  def __init__(self, i, e):
    self.i, self.e = i, e
    self.value = [i, e]
  def __repr__(self):
    return 'Typ(%s)' % (self.value,)


class Array:
  def __init__(self, i, e):
    self.i, self.e = i, e
    self.value = [i, e]
  def __repr__(self):
    return 'Array(%s)' % (self.value,)


