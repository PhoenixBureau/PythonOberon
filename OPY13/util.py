from struct import pack, unpack
from myhdl import Signal, intbv


ops = dict(
  Mov = 0, Lsl = 1, Asr = 2, Ror= 3, And = 4, Ann = 5, Ior = 6, Xor = 7,
  Add = 8, Sub = 9, Mul = 10, Div = 11,
  Fad = 12, Fsb = 13, Fml = 14, Fdv = 15,
  )
ops_rev = dict((v, k) for k, v in ops.iteritems())


word = lambda n: intbv(n, min=0, max=2**32)


ibv = lambda bits, n=0: Signal(intbv(n, min=0, max=2**bits))


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


def signed(n, bits=16):
  limit = 2**bits
  if -limit < n < limit:
    q = ((n < 0) << (bits - 1)) + abs(n)
    return intbv(q)[bits:]
  raise ValueError


def bits2signed_int(i):
  if not isinstance(i, intbv):
    raise ValueError("Must be intbv object. %r" % (i,))
  n = len(i)
  if not n:
    raise ValueError("Must have non-zero length. %r" % (i,))
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



if __name__ == '__main__':
  for n in xrange(2**32):
    print n, decode_set(n)
