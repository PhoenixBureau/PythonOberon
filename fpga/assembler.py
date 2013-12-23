from myhdl import intbv, concat


ops = dict(
  Mov = 0, Lsl = 1, Asr = 2, Ror= 3, And = 4, Ann = 5, Ior = 6, Xor = 7,
  Add = 8, Sub = 9, Mul = 10, Div = 11,
  )
word = lambda n: intbv(n, min=0, max=2**32)


def signed(n, bits=16):
  limit = 2**bits
  if -limit < n < limit:
    return ((n < 0) << bits) + abs(n)
  raise ValueError


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


def Mov(a, c, u=0): return make_F0(u, 0, a, 0, c)
def Lsl(a, b, c, u=0): return make_F0(u, 1, a, b, c)
def Asr(a, b, c, u=0): return make_F0(u, 2, a, b, c)
def Ror(a, b, c, u=0): return make_F0(u, 3, a, b, c)
def And(a, b, c, u=0): return make_F0(u, 4, a, b, c)
def Ann(a, b, c, u=0): return make_F0(u, 5, a, b, c)
def Ior(a, b, c, u=0): return make_F0(u, 6, a, b, c)
def Xor(a, b, c, u=0): return make_F0(u, 7, a, b, c)
def Add(a, b, c, u=0): return make_F0(u, 8, a, b, c)
def Sub(a, b, c, u=0): return make_F0(u, 9, a, b, c)
def Mul(a, b, c, u=0): return make_F0(u, 10, a, b, c)
def Div(a, b, c, u=0): return make_F0(u, 11, a, b, c)


def make_F1(u, v, op, a, b, K):
  assert bool(u) == u, repr(u)
  assert bool(v) == v, repr(v)
  assert ops['Mov'] <= op <= ops['Div'], repr(op)
  assert 0 <= a < 0x10, repr(a)
  assert 0 <= b < 0x10, repr(b)
  assert 0 <= abs(K) < 2**16, repr(K)
  return word(
    (1 << 30) + # set q
    (u << 29) +
    (v << 28) +
    (a << 24) +
    (b << 20) +
    (op << 16) +
    signed(K)
    )


def Mov_imm(a, K, v=0, u=0): return make_F1(u, v, 0, a, 0, K)
def Lsl_imm(a, b, K, v=0, u=0): return make_F1(u, v, 1, a, b, K)
def Asr_imm(a, b, K, v=0, u=0): return make_F1(u, v, 2, a, b, K)
def Ror_imm(a, b, K, v=0, u=0): return make_F1(u, v, 3, a, b, K)
def And_imm(a, b, K, v=0, u=0): return make_F1(u, v, 4, a, b, K)
def Ann_imm(a, b, K, v=0, u=0): return make_F1(u, v, 5, a, b, K)
def Ior_imm(a, b, K, v=0, u=0): return make_F1(u, v, 6, a, b, K)
def Xor_imm(a, b, K, v=0, u=0): return make_F1(u, v, 7, a, b, K)
def Add_imm(a, b, K, v=0, u=0): return make_F1(u, v, 8, a, b, K)
def Sub_imm(a, b, K, v=0, u=0): return make_F1(u, v, 9, a, b, K)
def Mul_imm(a, b, K, v=0, u=0): return make_F1(u, v, 10, a, b, K)
def Div_imm(a, b, K, v=0, u=0): return make_F1(u, v, 11, a, b, K)


def make_F3(cond, c, invert=False, v=False):
  # v = True -> PC to be stored in register R15
  assert 0 <= cond < 0x111, repr(cond)
  assert 0 <= c < 0x10, repr(c)
  assert bool(invert) == invert, repr(invert)
  assert bool(v) == v, repr(v)
  return word(
    (0b11 << 30) + # set p, q
    (v << 28) +
    (invert << 27) +
    (cond << 24) +
    c
    )


def MI(c): return make_F3(0, c)
def PL(c): return make_F3(0, c, True)
def EQ(c): return make_F3(1, c)
def NE(c): return make_F3(1, c, True)
def CS(c): return make_F3(2, c)
def CC(c): return make_F3(2, c, True)
def VS(c): return make_F3(3, c)
def VC(c): return make_F3(3, c, True)
def LS(c): return make_F3(4, c)
def HI(c): return make_F3(4, c, True)
def LT(c): return make_F3(5, c)
def GE(c): return make_F3(5, c, True)
def LE(c): return make_F3(6, c)
def GT(c): return make_F3(6, c, True)
def T(c): return make_F3(7, c)
def F(c): return make_F3(7, c, True)


def MI_link(c): return make_F3(0, c, v=True)
def PL_link(c): return make_F3(0, c, True, True)
def EQ_link(c): return make_F3(1, c, v=True)
def NE_link(c): return make_F3(1, c, True, True)
def CS_link(c): return make_F3(2, c, v=True)
def CC_link(c): return make_F3(2, c, True, True)
def VS_link(c): return make_F3(3, c, v=True)
def VC_link(c): return make_F3(3, c, True, True)
def LS_link(c): return make_F3(4, c, v=True)
def HI_link(c): return make_F3(4, c, True, True)
def LT_link(c): return make_F3(5, c, v=True)
def GE_link(c): return make_F3(5, c, True, True)
def LE_link(c): return make_F3(6, c, v=True)
def GT_link(c): return make_F3(6, c, True, True)
def T_link(c): return make_F3(7, c, v=True)
def F_link(c): return make_F3(7, c, True, True)

##  ((cc == 0) & N | // MI, PL
##   (cc == 1) & Z | // EQ, NE
##   (cc == 2) & C | // CS, CC
##   (cc == 3) & OV | // VS, VC
##   (cc == 4) & (C|Z) | // LS, HI
##   (cc == 5) & S | // LT, GE
##   (cc == 6) & (S|Z) | // LE, GT
##   (cc == 7)); // T, F


if __name__ == '__main__':
  mem = {}
  for i, instruction in enumerate((
    Mov_imm(8, 1),
    Mov_imm(7, 1),
    Add(1, 7, 8),
    Lsl_imm(1, 1, 2),
    T_link(1),
    )):
    print instruction, bin(instruction)
    mem[i] = instruction
