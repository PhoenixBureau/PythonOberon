from myhdl import Signal, intbv

ops = dict(
  Mov = 0, Lsl = 1, Asr = 2, Ror= 3, And = 4, Ann = 5, Ior = 6, Xor = 7,
  Add = 8, Sub = 9, Mul = 10, Div = 11,
  )
ops_rev = dict((v, k) for k, v in ops.iteritems())


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

