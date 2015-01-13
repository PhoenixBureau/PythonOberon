from math import log, floor
from struct import pack, unpack


ops = dict(
  Mov = 0, Lsl = 1, Asr = 2, Ror= 3, And = 4, Ann = 5, Ior = 6, Xor = 7,
  Add = 8, Sub = 9, Mul = 10, Div = 11,
  Fad = 12, Fsb = 13, Fml = 14, Fdv = 15,
  )
ops_rev = dict((v, k) for k, v in ops.iteritems())


word = lambda n: bint(n)


ibv = lambda bits, n=0: bint(n)


##  ((cc == 0) & N | // MI, PL
##   (cc == 1) & Z | // EQ, NE
##   (cc == 2) & C | // CS, CC
##   (cc == 3) & OV | // VS, VC
##   (cc == 4) & (C|Z) | // LS, HI
##   (cc == 5) & S | // LT, GE
##   (cc == 6) & (S|Z) | // LE, GT
##   (cc == 7)); // T, F

cmps = {
  (0, 0): 'MI',
  (0, 1): 'PL',
  (1, 0): 'EQ',
  (1, 1): 'NE',
  (2, 0): 'CS',
  (2, 1): 'CC',
  (3, 0): 'VS',
  (3, 1): 'VC',
  (4, 0): 'LS',
  (4, 1): 'HI',
  (5, 0): 'LT',
  (5, 1): 'GE',
  (6, 0): 'LE',
  (6, 1): 'GT',
  (7, 0): 'T',
  (7, 1): 'F',
}


def py2signed(i, width=32):
  assert width > 0
  width -= 1
  b = 2**width
  if not (-b <= i < b):
    raise ValueError
  if i >= 0:
    return i
  return b + i + (1 << width)


def signed2py(i, width=32):
  assert width > 0
  b = 2**width
  if not (0 <= i < b):
    raise ValueError
  if i < b / 2:
    return i
  return i - b


def unsigned_to_signed(g):
  return unpack('<i', pack('<I', g))[0]


def signed_to_unsigned(g):
  return unpack('<I', pack('<i', g))[0]


def _show_signed_in_action():
  W = 4
  for i in range(-10, 10):
    print '%2i' % i,
    try: s = py2signed(i, W)
    except ValueError: print
    else: print '  ->  %04s aka %i  ->  %2i' % (
      bin(s)[2:], s, signed2py(s, W)
      )


def signed(n, bits=16):
  limit = 2**bits
  if -limit < n < limit:
    q = ((n < 0) << (bits - 1)) + abs(n)
    return bint(q)[bits:]
  raise ValueError


def bits2signed_int(i, n=32):
  if not isinstance(i, bint):
    raise ValueError("Must be bint object. %r" % (i,))
  n -= 1
  return (-1 if i[n] else 1) * i[n:]


def encode_float(f):
  return bits2signed_int(word(unpack('>I', pack('>f', f))[0]))

def decode_float(f):
  return unpack('>f', pack('>I', signed(f, 32)))[0]

def encode_set(s, size=32):
  return sum(1 << n for n in range(size) if n in s)

def decode_set(i, size=32):
  w = word(i)
  return {n for n in range(size) if w[n]}


##def log2(x):
##  y = 0
##  while x > 1:
##    x /= 2
##    y += 1
##  return y


def log2(x):
  return int(floor(log(x, 2)))


def word_print(it):
  b = bin(it)[2:]
  print (32 - len(b)) * '0' + b


class binary_addressing_mixin(object):

  def __getitem__(self, n):
    if isinstance(n, tuple):
      if len(n) != 2:
        raise IndexError('Must pass only two indicies.')
      start, stop = n
      return self._mask(stop, start - stop)

    if isinstance(n, slice):
      return self._getslice(n)

    return bool(self >> n & 1)

  def _getslice(self, s):
    if s.step:
      raise TypeError('Slice with step not supported.')

    start = 0 if s.start is None else s.start
    stop = 0 if s.stop is None else s.stop
    n = start - stop
    if n < 0:
      raise IndexError('Slice indexes should be left-to-right.')

    if not n:
      return type(self)(0)

    return self._mask(stop, n)

  def _mask(self, stop, n):
    return type(self)(self >> stop & (2**n - 1))


class bint(binary_addressing_mixin, int): pass
class blong(binary_addressing_mixin, long): pass


##if __name__ == '__main__':
##  for n in xrange(2**32):
##    print n, decode_set(n)
