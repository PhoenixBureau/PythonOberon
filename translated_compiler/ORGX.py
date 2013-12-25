'''
MODULE ORG; (* NW  10.10.2013  code generator in Oberon-07 for RISC*)
IMPORT SYSTEM, Files, ORS, ORB;
(*Code generator for Oberon compiler for RISC processor.
   Procedural interface to Parser OSAP; result in array "code".
   Procedure Close writes code-files*)
'''

import Files, ORSX as ORS, ORBX as ORB

WordSize = 4;
StkOrg0 = -64; VarOrg0 = 0; # (*for RISC-0 only*)
MT = 12; SB = 13; SP = 14; LNK = 15; #  (*dedicated registers*)
maxCode = 8000; maxStrx = 2400; maxTD = 120; C24 = 0x1000000;
Reg = 10; RegI = 11; Cond = 12; # (*internal item modes*)

#(*frequently used opcodes*)
U = 0x2000;
Mov = 0; Lsl = 1; Asr = 2; Ror= 3; And = 4; Ann = 5; Ior = 6; Xor = 7;
Add = 8; Sub = 9; Cmp = 9; Mul = 10; Div = 11;
Fad = 12; Fsb = 13; Fml = 14; Fdv = 15;
Ldr = 8; Str = 10;
BR = 0; BLR = 1; BC = 2; BL = 3;
MI = 0; PL = 8; EQ = 1; NE = 9; LT = 5; GE = 13; LE = 6; GT = 14;

class Item:
  def __init__(self,):
    self.mode = 0
    self.type_ = None
    self.a, self.b, self.r = 0,0,0
    self.rdo = False


##(* Item forms and meaning of fields:
##  mode    r      a       b
##  --------------------------------
##  Const   -     value (proc adr)   (immediate value)
##  Var     base   off     -               (direct adr)
##  Par      -     off0     off1         (indirect adr)
##  Reg    regno
##  RegI   regno   off     -
##  Cond  cond   Fchain  Tchain  *)


pc, varsize = 0,0 #  (*program counter, data index*)
tdx, strx = 0,0
entry = 0 # (*main entry point*)
RH = 0 # (*available registers R[0] ... R[H-1]*)
curSB = 0 # (*current static base in SB*)
fixorgP, fixorgD, fixorgT = 0,0,0 # (*origins of lists of locations to be fixed up by loader*)
check, inhibitCalls = False, False # (*emit run-time checks*)
version = 0 # (* 0 = RISC-0, 1 = RISC-5 *)

relmap = {} # (*condition codes for relations*)
relmap[0] = 1; relmap[1] = 9; relmap[2] = 5; relmap[3] = 6; relmap[4] = 14; relmap[5] = 13

code = {} # : ARRAY maxCode OF LONGINT;
data = {} # : ARRAY maxTD OF LONGINT;  (*type_ descriptors*)
str_ = {} # : ARRAY maxStrx OF 0xCAR;

#(*instruction assemblers according to formats*)

def Put0(op, a, b, c):
  # (*emit format-0 instruction*)
  global pc
  code[pc] = ((a*0x10 + b) * 0x10 + op) * 0x10000 + c; pc += 1

def Put1(op, a, b, im):
  # (*emit format-1 instruction,  -0x10000 <= im < 0x10000*)
  global pc
  if im < 0:
    op += 0x1000 # (*set v-bit*)
  code[pc] = (((a+0x40) * 0x10 + b) * 0x10 + op) * 0x10000 + (im % 0x10000); pc += 1

def Put1a(op, a, b, im):
  # (*same as Pu1, but with range test  -0x10000 <= im < 0x10000*)
  if (im >= -0x10000) and (im <= 0x0FFFF):
    Put1(op, a, b, im)
  else:
    Put1(Mov+U, RH, 0, im / 0x10000);
    if im % 0x10000 != 0:
      Put1(Ior, RH, RH, im % 0x10000)
    Put0(op, a, b, RH)

def Put2(op, a, b, off):
  # (*emit load/store instruction*)
  global pc
  code[pc] = ((op * 0x10 + a) * 0x10 + b) * 0x100000 + (off % 0x100000); pc += 1

def Put3(op, cond, off):
  # (*emit bran0xc instruction*)
  global pc
  code[pc] = ((op+12) * 0x10 + cond) * 0x1000000 + (off % 0x1000000); pc += 1

def incR():
  global RH
  if RH < MT:
    RH += 1
  else:
    ORS.Mark("register stack overflow")

def CheckRegs():
  global RH
  if RH != 0:
    ORS.Mark("Reg Stack")
    RH = 0
  if pc >= maxCode - 40:
    ORS.Mark("Program too long")


def SaveRegs(r): #(* R[0 .. r-1] to be saved; R[r .. RH-1] to be moved down*)
  global RH
  rs = r; rd = 0;
  while True:
    rs -= 1
    Put1(Sub, SP, SP, 4)
    Put2(Str, rs, SP, 0)
    if rs == 0:
      break
  rs = r; rd = 0;
  while rs < RH:
    Put0(Mov, rd, 0, rs)
    rs += 1
    rd += 1
  RH = rd


def RestoreRegs(r, x): # (*R[0 .. r-1] to be restored*)
  assert r > 0
  Put0(Mov, r, 0, 0)
  rd = 0
  while True:
    Put2(Ldr, rd, SP, 0)
    Put1(Add, SP, SP, 4)
    rd += 1
    if rd == r:
      break

def SetCC(x, n):
  x.mode = Cond; x.a = 0; x.b = 0; x.r = n

def Trap(cond, num):
  Put3(BLR, cond, ORS.Pos()*0x100 + num*0x10 + MT)

# (*handling of forward reference, fixups of branch addresses and constant tables*)

def negated(cond):
  if cond < 8:
    cond = cond+8
  else:
    cond = cond-8
  return cond

def invalSB():
  global curSB
  curSB = 1


def fix(at, with_):
  code[at] = code[at] / C24 * C24 + (with_ % C24)


def FixLink(L):
  invalSB()
  while L != 0:
    L1 = code[L] % 0x40000
    fix(L, pc-L-1)
    L = L1
  return L

def FixLinkWith(L0, dst):
  while L0 != 0:
    L1 = code[L0] % C24;
    code[L0] = code[L0] / C24 * C24 + ((dst - L0 - 1) % C24)
    L0 = L1


def merged(L0, L1):
  if L0 != 0:
    L3 = L0;
    while True:
      L2 = L3
      L3 = code[L2] % 0x40000
      if L3 == 0:
        break
    code[L2] = code[L2] + L1
    L1 = L0
  return L1


# (* loading of operands and addresses into registers *)

def GetSB(base):
  global fixorgD, curSB
  if (version != 0) and ((base != curSB) or (base != 0)):
    Put2(Ldr, SB, -base, pc-fixorgD)
    fixorgD = pc-1
    curSB = base


def NilCheck():
  if check:
    Trap(EQ, 4)


def load(x):
  if x.type_.size == 1:
    op = Ldr+1
  else:
    op = Ldr

  if x.mode != Reg:

    if x.mode == ORB.Var:
      if x.r > 0: # (*local*)
        Put2(op, RH, SP, x.a)
      else:
        GetSB(x.r);
        Put2(op, RH, SB, x.a)
      x.r = RH; incR()

    elif x.mode == ORB.Par:
      Put2(Ldr, RH, SP, x.a)
      Put2(op, RH, RH, x.b)
      x.r = RH; incR()

    elif x.mode == ORB.Const:

      if x.type_.form == ORB.Proc:
        if x.r > 0:
          ORS.Mark("not allowed")
        elif x.r == 0:
          Put3(BL, 7, 0)
          Put1a(Sub, RH, LNK, pc*4 - x.a)
        else:
          GetSB(x.r)
          Put1(Add, RH, SB, x.a + 0x100) # (*mark as progbase-relative*)

      elif (x.a <= 0x0FFFF) and (x.a >= -0x10000):
        Put1(Mov, RH, 0, x.a)

      else:
        Put1(Mov+U, RH, 0, x.a / 0x10000 % 0x10000);
        if x.a % 0x10000 != 0:
          Put1(Ior, RH, RH, x.a % 0x10000)

      x.r = RH; incR()

    elif x.mode == RegI:
      Put2(op, x.r, x.r, x.a)

    elif x.mode == Cond:
      Put3(BC, negated(x.r), 2)
      x.b = FixLink(x.b)
      Put1(Mov, RH, 0, 1)
      Put3(BC, 7, 1)
      x.a = FixLink(x.a)
      Put1(Mov, RH, 0, 0)
      x.r = RH; incR()

    x.mode = Reg


def loadAdr(x):
  if x.mode == ORB.Var:
    if x.r > 0: # (*local*)
      Put1a(Add, RH, SP, x.a)
    else:
      GetSB(x.r)
      Put1a(Add, RH, SB, x.a)
    x.r = RH; incR()

  elif x.mode == ORB.Par:
    Put2(Ldr, RH, SP, x.a);
    if x.b != 0:
      Put1a(Add, RH, RH, x.b)
    x.r = RH; incR()

  elif x.mode == RegI:
    if x.a != 0:
      Put1a(Add, x.r, x.r, x.a)

  else:
    ORS.Mark("address error") 

  x.mode = Reg


def loadCond(x):
  global RH
  if x.type_.form == ORB.Bool:
    if x.mode == ORB.Const:
      x.r = 15 - x.a*8
    else:
      load(x)
      if code[pc-1] / 0x40000000 != -2:
        Put1(Cmp, x.r, x.r, 0)
      x.r = NE
      RH -= 1

    x.mode = Cond
    x.a = 0
    x.b = 0
  else:
    ORS.Mark("not Boolean?")


def loadTypTagAdr(T):
  x = Item()
  x.mode = ORB.Var; x.a = T.len_; x.r = -T.mno
  loadAdr(x)


def loadStringAdr(x):
  GetSB(0)
  Put1a(Add, RH, SB, varsize+x.a)
  x.mode = Reg
  x.r = RH; incR()


# (* Items: Conversion from constants or from Objects on the Heap to Items on the Stack*)

def MakeConstItem(x, typ, val):
  x.mode = ORB.Const; x.type_ = typ; x.a = val


def MakeRealItem(x, val):
  x.mode = ORB.Const; x.type_ = ORB.realType; x.a = SYSTEM.VAL(LONGINT, val)


def MakeStringItem(x, len_): # (*copies string from ORS-buffer to ORG-string array*)
  global strx
  x.mode = ORB.Const
  x.type_ = ORB.strType
  x.a = strx
  x.b = len_
  i = 0
  if strx + len_ + 4 < maxStrx:
    while len_ > 0:
      str_[strx] = ORS.str_[i]
      strx += 1
      i += 1
      len_ -= 1
    while strx % 4 != 0:
      str_[strx] = 0x0
      strx += 1
  else:
    ORS.Mark("too many strings")


def MakeItem(x, y, curlev):
  x.mode = y.class_
  x.type_ = y.type_
  x.a = y.val
  x.rdo = y.rdo;

  if y.class_ == ORB.Par:
    x.b = 0
  elif y.class_ == ORB.Typ:
    x.a = y.type_.len_
    x.r = -y.lev
  elif (y.class_ == ORB.Const) and (y.type_.form == ORB.String):
    x.b = y.lev # (*len_*)
  else:
    x.r = y.lev

  if (y.lev > 0) and (y.lev != curlev) and (y.class_ != ORB.Const):
    ORS.Mark("level error, not accessible")


# (* Code generation for Selectors, Variables, Constants *)

def Field(x, y): # (* x = x.y *)
  if x.mode == ORB.Var:
    if x.r >= 0:
      x.a = x.a + y.val
    else:
      loadAdr(x)
      x.mode = RegI
      x.a = y.val
  elif x.mode == RegI:
    x.a = x.a + y.val
  elif x.mode == ORB.Par:
    x.b = x.b + y.val


def Index(x, y): # (* x = x[y] *)
  global RH
  s = x.type_.base.size
  lim = x.type_.len_
  if (y.mode == ORB.Const) and (lim >= 0):
    if (y.a < 0) or (y.a >= lim):
      ORS.Mark("bad index")
    if x.mode in [ORB.Var, RegI]:
      x.a = y.a * s + x.a
    elif x.mode == ORB.Par:
      x.b = y.a * s + x.b

  else:
    load(y);
    if check: # (*check array bounds*)
      if lim >= 0:
        Put1a(Cmp, RH, y.r, lim)
      else: # (*open array*)
        if x.mode in [ORB.Var, ORB.Par]:
          Put2(Ldr, RH, SP, x.a+4)
          Put0(Cmp, RH, y.r, RH)
        else:
          ORS.Mark("error in Index")
      Trap(10, 1)

    if s == 4:
      Put1(Lsl, y.r, y.r, 2)
    elif s > 1:
      Put1(Mul, y.r, y.r, s)

    if x.mode == ORB.Var:
      if x.r > 0:
        Put0(Add, y.r, SP, y.r)
      else:
        GetSB(x.r);
        if x.r == 0:
          Put0(Add, y.r, SB, y.r)
        else:
          Put1a(Add, RH, SB, x.a)
          Put0(Add, y.r, RH, y.r)
          x.a = 0
      x.r = y.r
      x.mode = RegI

    elif x.mode == ORB.Par:
      Put2(Ldr, RH, SP, x.a);
      Put0(Add, y.r, RH, y.r)
      x.mode = RegI
      x.r = y.r; x.a = x.b

    elif x.mode == RegI:
      Put0(Add, x.r, x.r, y.r)
      RH -= 1


def DeRef(x):
  if x.mode == ORB.Var:
    if x.r > 0: # (*local*)
      Put2(Ldr, RH, SP, x.a)
    else:
      GetSB(x.r)
      Put2(Ldr, RH, SB, x.a)
    NilCheck()
    x.r = RH
    incR()

  elif x.mode == ORB.Par:
    Put2(Ldr, RH, SP, x.a)
    Put2(Ldr, RH, RH, x.b)
    NilCheck()
    x.r = RH
    incR()

  elif x.mode == RegI:
    Put2(Ldr, x.r, x.r, x.a)
    NilCheck()

  elif x.mode != Reg:
    ORS.Mark("bad mode in DeRef")

  x.mode = RegI; x.a = 0; x.b = 0


def Q(T, dcw):
  global fixorgT
  # (*one entry of type_ descriptor extension table*)
  if T.base != None:
    dcw = Q(T.base, dcw)
    data[dcw] = (T.mno*0x1000 + T.len_) * 0x1000 + dcw - fixorgT
    fixorgT = dcw
    dcw += 1
  return dcw


def FindPtrFlds(typ, off, dcw):
  if (typ.form == ORB.Pointer) or (typ.form == ORB.NilTyp):
    data[dcw] = off
    dcw += 1
  elif typ.form == ORB.Record:
    fld = typ.dsc;
    while fld != None:
      dcw = FindPtrFlds(fld.type_, fld.val + off, dcw)
      fld = fld.next
  elif typ.form == ORB.Array:
    s = typ.base.size;
    for i in range(typ.len_):
      dcw = FindPtrFlds(typ.base, i*s + off, dcw)
  return dcw


def BuildTD(T, dc):
  # (*dcw == word address*)
  dcw = dc / 4
  s = T.size # (*convert size for heap allocation*)
  if s <= 24:
    s = 32
  elif s <= 56:
    s = 64
  elif s <= 120:
    s = 128
  else:
    s = (s+263) / 256 * 256

  data[dcw] = s
  dcw += 1;
  k = T.nofpar #  (*extension level!*)
  if k > 3:
    ORS.Mark("ext level too large")
  else:
    dcw = Q(T, dcw);
    while k < 3:
      data[dcw] = -1
      dcw += 1
      k += 1

  dcw = FindPtrFlds(T, 0, dcw)
  data[dcw] = -1
  dcw += 1
  tdx = dcw
  dc = dcw*4
  if tdx >= maxTD:
    ORS.Mark("too many record types");
    tdx = 0

  return dc


def TypeTest(x, T, varpar, isguard):
  global RH
  # (*fetch tag into RH*)
  if varpar:
    Put2(Ldr, RH, SP, x.a+4)
  else:
    load(x)
    NilCheck()
    Put2(Ldr, RH, x.r, -8)

  Put2(Ldr, RH, RH, T.nofpar*4); incR();
  loadTypTagAdr(T) # (*tag of T*)
  Put0(Cmp, RH, RH-1, RH-2)
  RH -= 2;
  if isguard:
    if check:
      Trap(NE, 2)
  else:
    SetCC(x, EQ)
    if not varpar:
      RH -= 1


# (* Code generation for Boolean operators *)

def Not(x): # (* x = ~x *)
  if x.mode != Cond:
    loadCond(x)
  x.r = negated(x.r);
  t = x.a; x.a = x.b; x.b = t


def And1(x): # (* x = x and *)
  if x.mode != Cond:
    loadCond(x)
  Put3(BC, negated(x.r), x.a)
  x.a = pc-1; x.b = FixLink(x.b); x.b = 0


def And2(x, y):
  if y.mode != Cond:
    loadCond(y)
  x.a = merged(y.a, x.a); x.b = y.b; x.r = y.r


def Or1(x):#   (* x = x or *)
  if x.mode != Cond:
    loadCond(x)
  Put3(BC, x.r, x.b)
  x.b = pc-1; x.a = FixLink(x.a); x.a = 0


def Or2(x, y):
  if y.mode != Cond:
    loadCond(y)
  x.a = y.a; x.b = merged(y.b, x.b); x.r = y.r


# (* Code generation for arithmetic operators *)

def Neg(x): # (* x = -x *)
  if x.type_.form == ORB.Int:
    if x.mode == ORB.Const:
      x.a = -x.a
    else:
      load(x)
      Put1(Mov, RH, 0, 0)
      Put0(Sub, x.r, RH, x.r)

  elif x.type_.form == ORB.Real:
    if x.mode == ORB.Const:
      x.a = x.a + 0x7FFFFFFF + 1
    else:
      load(x)
      Put1(Mov, RH, 0, 0)
      Put0(Fsb, x.r, RH, x.r)

  else: # (*form == Set*)
    if x.mode == ORB.Const:
      x.a = -x.a-1 
    else:
      load(x)
      Put1(Xor, x.r, x.r, -1)


def AddOp(op, x, y): # (* x = x +- y *)
  global RH
  if op == ORS.plus:
    if (x.mode == ORB.Const) and (y.mode == ORB.Const):
      x.a = x.a + y.a
    elif y.mode == ORB.Const:
      load(x);
      if y.a != 0:
        Put1a(Add, x.r, x.r, y.a)
    else:
      load(x)
      load(y)
      Put0(Add, RH-2, x.r, y.r)
      RH -= 1
      x.r = RH-1

  else: # (*op == ORS.minus*)
    if (x.mode == ORB.Const) and (y.mode == ORB.Const):
      x.a = x.a - y.a
    elif y.mode == ORB.Const:
      load(x);
      if y.a != 0:
        Put1a(Sub, x.r, x.r, y.a)
    else:
      load(x)
      load(y)
      Put0(Sub, RH-2, x.r, y.r)
      RH -= 1
      x.r = RH-1


def log2(m, e): # FIXME e is VAR
  e = 0
  while not ODD(m):
    m = m / 2
    e += 1
  return m


def MulOp(x, y): # (* x = x * y *)
  global RH
  if (x.mode == ORB.Const) and (y.mode == ORB.Const):
    x.a = x.a * y.a
  elif (y.mode == ORB.Const) and (y.a >= 2) and (log2(y.a, e) == 1):
    load(x)
    Put1(Lsl, x.r, x.r, e)
  elif y.mode == ORB.Const:
    load(x)
    Put1a(Mul, x.r, x.r, y.a)
  elif (x.mode == ORB.Const) and (x.a >= 2) and (log2(x.a, e) == 1):
    load(y)
    Put1(Lsl, y.r, y.r, e)
    x.mode = Reg
    x.r = y.r
  elif x.mode == ORB.Const:
    load(y)
    Put1a(Mul, y.r, y.r, x.a)
    x.mode = Reg
    x.r = y.r
  else:
    load(x)
    load(y)
    Put0(Mul, RH-2, x.r, y.r)
    RH -= 1
    x.r = RH-1


def DivOp(op, x, y): # (* x = x op y *)
  global RH
  if op == ORS.div:
    if (x.mode == ORB.Const) and (y.mode == ORB.Const):
      if y.a > 0:
        x.a = x.a / y.a
      else:
        ORS.Mark("bad divisor")
    elif (y.mode == ORB.Const) and (y.a >= 2) and (log2(y.a, e) == 1):
      load(x)
      Put1(Asr, x.r, x.r, e)
    elif y.mode == ORB.Const:
      if y.a > 0:
        load(x)
        Put1a(Div, x.r, x.r, y.a)
      else:
        ORS.Mark("bad divisor")
    else:
      load(y);
      if check:
        Trap(LE, 6)
      load(x)
      Put0(Div, RH-2, x.r, y.r)
      RH -= 1
      x.r = RH-1

  else: # (*op == ORS.mod*)
    if (x.mode == ORB.Const) and (y.mode == ORB.Const):
      if y.a > 0:
        x.a = x.a % y.a
      else:
        ORS.Mark("bad modulus")
    elif (y.mode == ORB.Const) and (y.a >= 2) and (log2(y.a, e) == 1):
      load(x);
      if e <= 16:
        Put1(And, x.r, x.r, y.a-1)
      else:
        Put1(Lsl, x.r, x.r, 32-e)
        Put1(Ror, x.r, x.r, 32-e)
    elif y.mode == ORB.Const:
      if y.a > 0:
        load(x)
        Put1a(Div, x.r, x.r, y.a)
        Put0(Mov+U, x.r, 0, 0)
      else:
        ORS.Mark("bad modulus")
    else:
      load(y);
      if check:
        Trap(LE, 6)
      load(x)
      Put0(Div, RH-2, x.r, y.r)
      Put0(Mov+U, RH-2, 0, 0)
      RH -= 1
      x.r = RH-1


# (* Code generation for REAL operators *)

def RealOp(op, x, y): # (* x = x op y *)
  global RH
  load(x)
  load(y);
  if op == ORS.plus:
    Put0(Fad, RH-2, x.r, y.r)
  elif op == ORS.minus:
    Put0(Fsb, RH-2, x.r, y.r)
  elif op == ORS.times:
    Put0(Fml, RH-2, x.r, y.r)
  elif op == ORS.rdiv:
    Put0(Fdv, RH-2, x.r, y.r)

  RH -= 1; x.r = RH-1


# (* Code generation for set operators *)

def Singleton(x): # (* x = {x} *)
  if x.mode == ORB.Const:
    x.a = LSL(1, x.a)
  else:
    load(x)
    Put1(Mov, RH, 0, 1)
    Put0(Lsl, x.r, RH,  x.r)


def Set(x, y): #   (* x = {x .. y} *)
  global RH
  if (x.mode == ORB.Const) and ( y.mode == ORB.Const):
    if x.a <= y.a:
      x.a = LSL(2, y.a) - LSL(1, x.a)
    else:
      x.a = 0
  else:
    if (x.mode == ORB.Const) and (x.a < 0x10):
      x.a = LSL(-1, x.a)
    else:
      load(x)
      Put1(Mov, RH, 0, -1)
      Put0(Lsl, x.r, RH, x.r)

    if (y.mode == ORB.Const) and (y.a < 0x10):
      Put1(Mov, RH, 0, LSL(-2, y.a))
      y.mode = Reg; y.r = RH; RH += 1
    else:
      load(y)
      Put1(Mov, RH, 0, -2)
      Put0(Lsl, y.r, RH, y.r)

    if x.mode == ORB.Const:
      if x.a != 0:
        Put1(Xor, y.r, y.r, -1)
        Put1a(And, RH-1, y.r, x.a)
      x.mode = Reg
      x.r = RH-1
    else:
      RH -= 1
      Put0(Ann, RH-1, x.r, y.r)


def In(x, y): #  (* x = x IN y *)
  global RH
  load(y)
  if x.mode == ORB.Const:
    Put1(Ror, y.r, y.r, (x.a + 1) % 0x20)
    RH -= 1
  else:
    load(x)
    Put1(Add, x.r, x.r, 1)
    Put0(Ror, y.r, y.r, x.r)
    RH -= 2
  SetCC(x, MI)


def SetOp(op, x, y): # (* x = x op y *)
  global RH
  if (x.mode == ORB.Const) and (y.mode == ORB.Const):
    xset = set(x.a)
    yset = set(y.a)
    if op == ORS.plus:
      xset = xset + yset
    elif op == ORS.minus:
      xset = xset - yset
    elif op == ORS.times:
      xset = xset & yset # FIXME I'm guessing; look it up
    elif op == ORS.rdiv:
      xset = xset ^ yset

    x.a = SYSTEM.VAL(LONGINT, xset) # FIXME explode!

  elif y.mode == ORB.Const:
    load(x);
    if op == ORS.plus:
      Put1a(Ior, x.r, x.r, y.a)
    elif op == ORS.minus:
      Put1a(Ann, x.r, x.r, y.a)
    elif op == ORS.times:
      Put1a(And, x.r, x.r, y.a)
    elif op == ORS.rdiv:
      Put1a(Xor, x.r, x.r, y.a)

  else:
    load(x)
    load(y)
    if op == ORS.plus:
      Put0(Ior, RH-2, x.r, y.r)
    elif op == ORS.minus:
      Put0(Ann, RH-2, x.r, y.r)
    elif op == ORS.times:
      Put0(And, RH-2, x.r, y.r)
    elif op == ORS.rdiv:
      Put0(Xor, RH-2, x.r, y.r)

    RH -= 1
    x.r = RH-1


# (* Code generation for relations *)

def IntRelation(op, x, y): # (* x = x < y *)
  global RH
  if (y.mode == ORB.Const) and (y.type_.form != ORB.Proc):
    load(x)
    if (y.a != 0) or (op not in [ORS.eql, ORS.neq]) or (code[pc-1] / 0x40000000 != -2):
      Put1a(Cmp, x.r, x.r, y.a)
    RH -= 1
  else:
    load(x)
    load(y)
    Put0(Cmp, x.r, x.r, y.r)
    RH -= 2
  SetCC(x, relmap[op - ORS.eql])
  return x, y


def SetRelation(op, x, y): #   (* x = x < y *)
  global RH
  load(x)
  if (op == ORS.eql) or (op == ORS.neq):
    if y.mode == ORB.Const:
      Put1a(Cmp, x.r, x.r, y.a)
      RH -= 1
    else:
      load(y)
      Put0(Cmp, x.r, x.r, y.r)
      RH -= 2
    SetCC(x, relmap[op - ORS.eql])
  else:
    ORS.Mark("illegal relation") 
  return x, y


def RealRelation(op, x, y): #   (* x = x < y *)
  global RH
  load(x)
  if (y.mode == ORB.Const) and (y.a == 0):
    RH -= 1
  else:
    load(y)
    Put0(Fsb, x.r, x.r, y.r)
    RH -= 2
  SetCC(x, relmap[op - ORS.eql])
  return x, y


def StringRelation(op, x, y): #  (* x = x < y *)
  global RH
  #(*x, y are char arrays or strings*)
  if x.type_.form == ORB.String:
    loadStringAdr(x)
  else:
    loadAdr(x)
  if y.type_.form == ORB.String:
    loadStringAdr(y)
  else:
    loadAdr(y)
  Put2(Ldr+1, RH, x.r, 0)
  Put1(Add, x.r, x.r, 1)
  Put2(Ldr+1, RH+1, y.r, 0)
  Put1(Add, y.r, y.r, 1)
  Put0(Cmp, RH+2, RH, RH+1)
  Put3(BC, NE, 2)
  Put1(Cmp, RH+2, RH, 0)
  Put3(BC, NE, -8)
  RH -= 2
  SetCC(x, relmap[op - ORS.eql])
  return x, y


# (* Code generation of Assignments *)


def StrToChar(x):
  global strx
  x.type_ = ORB.charType
  strx -= 4
  x.a = ORD(str_[x.a])


def Store(x, y): # (* x = y *)
  global RH
  #VAR op: LONGINT;
  load(y);
  if x.type_.size == 1:
    op = Str+1
  else:
    op = Str
  if x.mode == ORB.Var:
    if x.r > 0:  # (*local*)
      Put2(op, y.r, SP, x.a)
    else:
      GetSB(x.r)
      Put2(op, y.r, SB, x.a)
  elif x.mode == ORB.Par:
    Put2(Ldr, RH, SP, x.a)
    Put2(op, y.r, RH, x.b);
  elif x.mode == RegI:
    Put2(op, y.r, x.r, x.a)
    RH -= 1;
  else:
    ORS.Mark("bad mode in Store")
  RH -= 1


def StoreStruct(x, y): # (* x = y *)
  global RH
  # VAR s, pc0: LONGINT;
  loadAdr(x); loadAdr(y)
  if (x.type_.form == ORB.Array) and (x.type_.len_ > 0):
    if y.type_.len_ >= 0: 
      if x.type_.len_ >= y.type_.len_:
        Put1(Mov, RH, 0, (y.type_.size+3) / 4)
      else:
        ORS.Mark("source array too long")
    else: # (*y is open array*)
      Put2(Ldr, RH, SP, y.a+4)
      s = y.type_.base.size #  (*element size*)
      pc0 = pc
      Put3(BC, EQ, 0)
      if s == 1:
        Put1(Add, RH, RH, 3)
        Put1(Asr, RH, RH, 2)
      elif s != 4:
        Put1(Mul, RH, RH, s / 4)

      if check:
        Put1(Mov, RH+1, 0, (x.type_.size+3) / 4)
        Put0(Cmp, RH+1, RH, RH+1)
        Trap(GT, 3)

      fix(pc0, pc + 5 - pc0)

  elif x.type_.form == ORB.Record:
    Put1(Mov, RH, 0, x.type_.size / 4)
  else:
    ORS.Mark("inadmissible assignment")

  Put2(Ldr, RH+1, y.r, 0)
  Put1(Add, y.r, y.r, 4)
  Put2(Str, RH+1, x.r, 0)
  Put1(Add, x.r, x.r, 4)
  Put1(Sub, RH, RH, 1)
  Put3(BC, NE, -6)
  RH -= 2
  return x, y


def CopyString(x, y): # (*from x to y*)
  global RH
  #VAR len_: LONGINT;
  loadAdr(y)
  len_ = y.type_.len_
  if len_ >= 0:
    if x.b > len_:
      ORS.Mark("string too long")
  elif check:
    Put2(Ldr, RH, y.r, 4); # (*array length check*)
    Put1(Cmp, RH, RH, x.b)
    Trap(NE, 3)

  loadStringAdr(x)
  Put2(Ldr, RH, x.r, 0)
  Put1(Add, x.r, x.r, 4)
  Put2(Str, RH, y.r, 0)
  Put1(Add, y.r, y.r, 4)
  Put1(Asr, RH, RH, 24)
  Put3(BC, NE, -6)
  RH -= 2
  return x, y

# (* Code generation for parameters *)

def VarParam(x, ftype):
  #VAR xmd: INTEGER;
  xmd = x.mode
  loadAdr(x);
  if (ftype.form == ORB.Array) and (ftype.len_ < 0): # (*open array*)
    if x.type_.len_ >= 0:
      Put1(Mov, RH, 0, x.type_.len_)
    else:
      Put2(Ldr, RH, SP, x.a+4)
    incR()
  elif ftype.form == ORB.Record:
    if xmd == ORB.Par:
      Put2(Ldr, RH, SP, x.a+4);
      incR()
    else:
      loadTypTagAdr(x.type_)
  return x


def ValueParam(x):
  load(x)


def OpenArrayParam(x):
  loadAdr(x)
  if x.type_.len_ >= 0:
    Put1a(Mov, RH, 0, x.type_.len_)
  else:
    Put2(Ldr, RH, SP, x.a+4)
  incR()
  return x


def StringParam(x):
  loadStringAdr(x)
  Put1(Mov, RH, 0, x.b)
  incR() # (*len_*)
  return x


# (*For Statements*)

def For0(x, y):
  load(y)


def For1(x, y, z, w, L):
  global RH
  if z.mode == ORB.Const:
    Put1a(Cmp, RH, y.r, z.a)
  else:
    load(z)
    Put0(Cmp, RH-1, y.r, z.r)
    RH -= 1

  L = pc
  if w.a > 0:
    Put3(BC, GT, 0)
  elif w.a < 0:
    Put3(BC, LT, 0)
  else:
    ORS.Mark("zero increment")
    Put3(BC, MI, 0)

  Store(x, y)
  return x, y, z, w, L


def For2(x, y, w):
  global RH
  load(x)
  RH -= 1
  Put1a(Add, x.r, x.r, w.a)


# (* Branches, procedure calls, procedure prolog and epilog *)

def Here():
  invalSB()
  return pc


def FJump(L):
  Put3(BC, 7, L)
  return pc-1


def CFJump(x):
  if x.mode != Cond:
    loadCond(x)
  Put3(BC, negated(x.r), x.a)
  x.b = FixLink(x.b)
  x.a = pc-1


def BJump(L):
  Put3(BC, 7, L-pc-1)


def CBJump(x, L):
  if x.mode != Cond:
    loadCond(x)
  Put3(BC, negated(x.r), L-pc-1);
  x.b = FixLink(x.b)
  x.a = FixLinkWith(x.a, L)


def Fixup(x):
  x.a = FixLink(x.a)


def PrepCall(x):
  global RH
  if x.type_.form == ORB.Proc:
    if x.mode != ORB.Const:
      load(x)
      code[pc-1] = code[pc-1] + 0x0B000000
      x.r = 11
      RH -= 1
      inhibitCalls = True
      if check:
        Trap(EQ, 5)
  else:
    ORS.Mark("not a procedure")
  return RH


def Call(x, r):
  global RH, inhibitCalls
  if inhibitCalls and (x.r != 11):
    ORS.Mark("inadmissible call")
  else:
    inhibitCalls = False

  if r > 0:
    SaveRegs(r)

  if x.type_.form == ORB.Proc:
    if x.mode == ORB.Const:
      if x.r >= 0:
        Put3(BL, 7, (x.a / 4)-pc-1)
      else: # (*imported*)
        if pc - fixorgP < 0x1000:
          Put3(BL, 7, ((-x.r) * 0x100 + x.a) * 0x1000 + pc-fixorgP)
          fixorgP = pc-1
        else:
          ORS.Mark("fixup impossible")
    else:
      Put3(BLR, 7, x.r)
  else:
    ORS.Mark("not a procedure")

  if x.type_.base.form == ORB.NoTyp:
    RH = 0
  else:
    if r > 0:
      RestoreRegs(r, x)
    x.mode = Reg
    x.r = r
    RH = r+1

  invalSB()


def Enter(parblksize, locblksize, int_):
  #VAR a, r: LONGINT;
  invalSB()
  if not int_: # (*procedure prolog*)
    a = 4; r = 0;
    Put1(Sub, SP, SP, locblksize)
    Put2(Str, LNK, SP, 0)
    while a < parblksize:
      Put2(Str, r, SP, a)
      r += 1; a += 4
  else: # (*interrupt procedure*)
    Put1(Sub, SP, SP, 8)
    Put2(Str, 0, SP, 0)
    Put2(Str, 1, SP, 4)
    # (*R0 and R1 saved, but NOT LNK*)


def Return(form, x, size, int_):
  global RH
  if form != ORB.NoTyp:
    load(x)
  if not int_: # (*procedure epilog*)
    Put2(Ldr, LNK, SP, 0)
    Put1(Add, SP, SP, size)
    Put3(BR, 7, LNK)
  else: # (*interrupt*)
    Put2(Ldr, 1, SP, 4)
    Put2(Ldr, 0, SP, 0)
    Put1(Add, SP, SP, 8)
    Put3(BR, 7, 0x10)
  RH = 0

# (*In-line code procedures*)

def Increment(upordown, x, y):
  global RH
  # VAR op, zr, v: LONGINT;
  if upordown == 0:
    op = Add
  else:
    op = Sub

  v = x.type_ == ORB.byteType

  if y.type_.form == ORB.NoTyp:
    y.mode = ORB.Const
    y.a = 1

  if (x.mode == ORB.Var) and (x.r > 0):
    zr = RH
    Put2(Ldr+v, zr, SP, x.a)
    incR();
    if y.mode == ORB.Const:
      Put1(op, zr, zr, y.a)
    else:
      load(y)
      Put0(op, zr, zr, y.r)
      RH -= 1
    Put2(Str+v, zr, SP, x.a)
    RH -= 1
  else:
    loadAdr(x)
    zr = RH
    Put2(Ldr+v, RH, x.r, 0)
    incR();
    if y.mode == ORB.Const:
      Put1(op, zr, zr, y.a)
    else:
      load(y)
      Put0(op, zr, zr, y.r)
      RH -= 1
    Put2(Str+v, zr, x.r, 0)
    RH -= 2


def Include(inorex, x, y):
  global RH
  # VAR zr: LONGINT;
  loadAdr(x)
  zr = RH
  Put2(Ldr, RH, x.r, 0)
  incR() # (); # FIXME where did these extra parens come from?
  if inorex == 0: # (*include*)
    if y.mode == ORB.Const:
      Put1(Ior, zr, zr, LSL(1, y.a))
    else:
      load(y)
      Put1(Mov, RH, 0, 1)
      Put0(Lsl, y.r, RH, y.r)
      Put0(Ior, zr, zr, y.r)
      RH -= 1

  else: # (*exclude*)
    if y.mode == ORB.Const:
      Put1(And, zr, zr, -LSL(1, y.a)-1)
    else:
      load(y)
      Put1(Mov, RH, 0, 1)
      Put0(Lsl, y.r, RH, y.r)
      Put1(Xor, y.r, y.r, -1)
      Put0(And, zr, zr, y.r)
      RH -= 1

  Put2(Str, zr, x.r, 0)
  RH -= 2


def Assert(x):
  global RH
  # VAR cond: LONGINT;
  if x.mode != Cond:
    loadCond(x)
  if x.a == 0:
    cond = negated(x.r)
  else:
    Put3(BC, x.r, x.b)
    x.a = FixLink(x.a)
    x.b = pc-1
    cond = 7
  Trap(cond, 7)
  x.b = FixLink(x.b)


def New(x):
  global RH
  loadAdr(x)
  loadTypTagAdr(x.type_.base)
  Put3(BLR, 7, MT)
  RH = 0
  invalSB()


def Pack(x, y):
  global RH
  # VAR z: Item;
  z = x # FIXME is this a copy?
  load(x); load(y);
  Put1(Lsl, y.r, y.r, 23)
  Put0(Add, x.r, x.r, y.r)
  RH -= 1
  Store(z, x)


def Unpk(x, y):
  # VAR z, e0: Item;
  z = x # FIXME is this a copy?
  load(x)
  e0.mode = Reg
  e0.r = RH
  e0.type_ = ORB.intType;
  Put1(Asr, RH, x.r, 23)
  Put1(Sub, RH, RH, 127)
  Store(y, e0)
  incR();
  Put1(Lsl, RH, RH, 23)
  Put0(Sub, x.r, x.r, RH)
  Store(z, x)


def Led(x):
  global RH
  load(x)
  Put1(Mov, RH, 0, -60)
  Put2(Str, x.r, RH, 0)
  RH -= 1


def Get(x, y):
  load(x)
  x.type_ = y.type_
  x.mode = RegI
  x.a = 0
  Store(y, x)


def Put(x, y):
  load(x)
  x.type_ = y.type_
  x.mode = RegI
  x.a = 0
  Store(x, y)


def Copy(x, y, z):
  load(x); load(y);
  if z.mode == ORB.Const:
    if z.a > 0:
      load(z)
    else:
      ORS.Mark("bad count")
  else:
    load(z)
    if check:
      Trap(LT, 3)
    Put3(BC, EQ, 6)

  Put2(Ldr, RH, x.r, 0)
  Put1(Add, x.r, x.r, 4)
  Put2(Str, RH, y.r, 0)
  Put1(Add, y.r, y.r, 4)
  Put1(Sub, z.r, z.r, 1)
  Put3(BC, NE, -6)
  RH -= 3


def LDPSR(x):
  # (*x.mode == Const*)
  Put3(0, 15, x.a + 0x20)


def LDREG(x, y):
  if y.mode == ORB.Const:
    Put1a(Mov, x.a, 0, y.a)
  else:
    load(y)
    Put0(Mov, x.a, 0, y.r)
    RH -= 1


# (*In-line code functions*)

def Abs(x):
  if x.mode == ORB.Const:
    x.a = ABS(x.a)
  else:
    load(x);
    if x.type_.form == ORB.Real:
      Put1(Lsl, x.r, x.r, 1)
      Put1(Ror, x.r, x.r, 1)
    else:
      Put1(Cmp, x.r, x.r, 0)
      Put3(BC, GE, 2)
      Put1(Mov, RH, 0, 0)
      Put0(Sub, x.r, RH, x.r)


def Odd(x):
  global RH
  load(x)
  Put1(And, x.r, x.r, 1)
  SetCC(x, NE)
  RH -= 1


def Floor(x):
  load(x)
  Put1(Mov+U, RH, 0, 0x4B00)
  Put0(Fad+0x1000, x.r, x.r, RH) 


def Float(x):
  load(x)
  Put1(Mov+U, RH, 0, 0x4B00)
  Put0(Fad+U, x.r, x.r, RH)


def Ord(x):
  if x.mode in {ORB.Var, ORB.Par, RegI}:
    load(x)


def Len(x):
  if x.type_.len_ >= 0:
    x.mode = ORB.Const
    x.a = x.type_.len_
  else: # (*open array*)
    Put2(Ldr, RH, SP, x.a + 4)
    x.mode = Reg
    x.r = RH
    incR()


def Shift(fct, x, y):
  global RH
  # VAR op: LONGINT;
  load(x);
  if fct == 0:
    op = Lsl
  elif fct == 1:
    op = Asr
  else:
    op = Ror
  if y.mode == ORB.Const:
    Put1(op, x.r, x.r, y.a % 0x20)
  else:
    load(y)
    Put0(op, RH-2, x.r, y.r)
    RH -= 1
    x.r = RH-1


def ADC(x, y):
  global RH
  load(x); load(y)
  Put0(Add+0x2000, x.r, x.r, y.r)
  RH -= 1


def SBC(x, y):
  global RH
  load(x); load(y)
  Put0(Sub+0x2000, x.r, x.r, y.r)
  RH -= 1


def UML(x, y):
  global RH
  load(x); load(y)
  Put0(Mul+0x2000, x.r, x.r, y.r)
  RH -= 1


def Bit(x, y):
  global RH
  load(x)
  Put2(Ldr, x.r, x.r, 0);
  if y.mode == ORB.Const:
    Put1(Ror, x.r, x.r, y.a+1)
    RH -= 1
  else:
    load(y)
    Put1(Add, y.r, y.r, 1)
    Put0(Ror, x.r, x.r, y.r)
    RH -= 2

  SetCC(x, MI)


def Register(x):
  # (*x.mode == Const*)
  Put0(Mov, RH, 0, x.a % 0x10)
  x.mode = Reg
  x.r = RH
  incR()


def H(x):
  # (*x.mode == Const*)
  Put0(Mov + U + (x.a % 2 * 0x1000), RH, 0, 0)
  x.mode = Reg
  x.r = RH
  incR()


def Adr(x):
  if x.mode in {ORB.Var, ORB.Par, RegI}:
    loadAdr(x)
  elif (x.mode == ORB.Const) and (x.type_.form == ORB.Proc):
    load(x)
  elif (x.mode == ORB.Const) and (x.type_.form == ORB.String):
    loadStringAdr(x)
  else:
    ORS.Mark("not addressable")


def Condition(x):
  # (*x.mode == Const*)
  SetCC(x, x.a)


def Open(v):
  global pc, tdx, strx, RH, fixorgP, fixorgD, fixorgT
  global check, version, inhibitCalls
  pc = tdx = strx = RH = fixorgP = fixorgD = fixorgT = 0
  check = v != 0
  version = v
  inhibitCalls = False
  if v == 0:
    pc = 8


def SetDataSize(dc):
  global varsize
  varsize = dc


def Header():
  global entry
  entry = pc*4;
  if version == 0:
    code[0] = 0x0E7000000-1 + pc
    Put1(Mov, SB, 0, 16)
    Put1(Mov, SP, 0, StkOrg0) # (*RISC-0*)
  else:
    Put1(Sub, SP, SP, 4)
    Put2(Str, LNK, SP, 0)
    invalSB()


def NofPtrs(typ):
  # VAR fld: ORB.Object; n: LONGINT;
  if (typ.form == ORB.Pointer) or (typ.form == ORB.NilTyp):
    n = 1
  elif typ.form == ORB.Record:
    fld = typ.dsc
    n = 0;
    while fld != None:
      n = NofPtrs(fld.type_) + n
      fld = fld.next
  elif typ.form == ORB.Array:
    n = NofPtrs(typ.base) * typ.len_
  else:
    n = 0

  return n


def FindPtrs(R, typ, adr):
  # VAR fld: ORB.Object; i, s: LONGINT;
  if (typ.form == ORB.Pointer) or (typ.form == ORB.NilTyp):
    Files.WriteInt(R, adr)
  elif typ.form == ORB.Record:
    fld = typ.dsc
    while fld != None:
      FindPtrs(R, fld.type_, fld.val + adr)
      fld = fld.next
  elif typ.form == ORB.Array:
    s = typ.base.size;
    for i in range(typ.len_):
      FindPtrs(R, typ.base, i*s + adr)


def Close(modid, key, nofent):
##  VAR obj: ORB.Object;
##    i, comsize, nofimps, nofptrs, size: LONGINT;
##    name: ORS.Ident;
##    F: Files.File; R: Files.Rider;

  #  (*exit code*)
  if version == 0:
    Put1(Mov, 0, 0, 0)
    Put3(BR, 7, 0) # (*RISC-0*)
  else:
    Put2(Ldr, LNK, SP, 0)
    Put1(Add, SP, SP, 4)
    Put3(BR, 7, LNK)

  obj = ORB.topScope.next
  nofimps = 0
  comsize = 4
  nofptrs = 0

  while obj != None:
    if (obj.class_ == ORB.Mod) and (obj.dsc != ORB.system):
      nofimps += 1 # (*count imports*)
    elif (
      (obj.exno != 0) and
      (obj.class_ == ORB.Const) and
      (obj.type_.form == ORB.Proc) and
      (obj.type_.nofpar == 0) and
      (obj.type_.base == ORB.noType)
      ):
      i = 0 # (*count commands*)
      while obj.name[i] != 0x0:
        i += 1
      i = (i+4) / 4 * 4
      comsize += i+4
    elif obj.class_ == ORB.Var:
      nofptrs += NofPtrs(obj.type_) # (*count pointers*)

    obj = obj.next

  size = varsize + strx + comsize + (pc + nofimps + nofent + nofptrs + 1)*4 # (*varsize includes type_ descriptors*)

  ORB.MakeFileName(name, modid, ".rsc") # (*write code file*)

  F = Files.New(name)
  Files.Set(R, F, 0)
  Files.WriteString(R, modid)
  Files.WriteInt(R, key)
  Files.WriteByte(R, version);
  Files.WriteInt(R, size);

  obj = ORB.topScope.next;
  while (obj != None) and (obj.class_ == ORB.Mod): # (*imports*)
    if obj.dsc != ORB.system:
      Files.WriteString(R, obj(ORB.Module).orgname)
      Files.WriteInt(R, obj.val)
    obj = obj.next

  Files.Write(R, 0x0);
  Files.WriteInt(R, tdx*4);

  i = 0;
  while i < tdx:
    Files.WriteInt(R, data[i])
    i += 1 # (*type_ descriptors*)

  Files.WriteInt(R, varsize - tdx*4) # (*data*)
  Files.WriteInt(R, strx)

  for i in range(strx):
    Files.Write(R, str_[i]) # (*strings*)

  Files.WriteInt(R, pc) # (*code len_*)
  for i in range(pc):
    Files.WriteInt(R, code[i]) # (*program*)

  obj = ORB.topScope.next
  while obj != None: # (*commands*)
    if (
      (obj.exno != 0) and
      (obj.class_ == ORB.Const) and
      (obj.type_.form == ORB.Proc) and
      (obj.type_.nofpar == 0) and
      (obj.type_.base == ORB.noType)
      ):
      Files.WriteString(R, obj.name)
      Files.WriteInt(R, obj.val)
    obj = obj.next

  Files.Write(R, 0x0)
  Files.WriteInt(R, nofent)
  Files.WriteInt(R, entry)

  obj = ORB.topScope.next;
  while obj != None: # (*entries*)
    if obj.exno != 0:
      if (obj.class_ == ORB.Const) and (obj.type_.form == ORB.Proc) or (obj.class_ == ORB.Var):
        Files.WriteInt(R, obj.val)
      elif obj.class_ == ORB.Typ:
        if obj.type_.form == ORB.Record:
          Files.WriteInt(R,  obj.type_.len_ % 0x10000)
        elif (obj.type_.form == ORB.Pointer) and ((obj.type_.base.typobj == None) or (obj.type_.base.typobj.exno == 0)):
          Files.WriteInt(R, obj.type_.base.len_ % 0x10000)

    obj = obj.next

  obj = ORB.topScope.next;
  while obj != None: # (*pointer variables*)
    if obj.class_ == ORB.Var:
      FindPtrs(R, obj.type_, obj.val)
    obj = obj.next

  Files.WriteInt(R, -1)
  Files.WriteInt(R, fixorgP)
  Files.WriteInt(R, fixorgD)
  Files.WriteInt(R, fixorgT)
  Files.WriteInt(R, entry)
  Files.Write(R, "O")

  Files.Register(F)

