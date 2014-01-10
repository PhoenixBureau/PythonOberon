##!=!=MODULE ORP; (*N. Wirth 1.7.97 / 5.11.2013  Oberon compiler for RISC in Oberon-07*)
##!=!=  IMPORT Texts, Oberon, ORS, ORB, ORG;
##!=!=  (*Author: Niklaus Wirth, 2011.
##!=!=    Parser of Oberon-RISC compiler. Uses Scanner ORS to obtain symbols (tokens),
##!=!=    ORB for definition of data structures and for handling import and export, and
##!=!=    ORG to produce binary code. ORP performs type_ checking and data allocation.
##!=!=    Parser is target-independent, except for part of the handling of allocations.*)
##!=!=
from copy import copy
import ORSX as ORS, ORBX as ORB, ORGX as ORG
##TYPE PtrBase == POINTER TO PtrBaseDesc;
##  PtrBaseDesc == RECORD  (*list of names of pointer base types*)
##    name: ORS.Ident; type_: ORB.Type; next: PtrBase
##  END ;
##
##VAR

class PtrBase(object):
  def __init__(self,):
    self.name = ''
    self.type_ = self.next = None


sym = 0 #  (*last symbol read*)
dc = 0 #: LONGINT;   # (*data counter*)
level, exno, version = 0, 0, 0 #: INTEGER;
newSF = False # : BOOLEAN; # (*option flag*)
modid = [] # : # ORS.Ident;
pbsList = None # : # PtrBase;  # (*list of names of pointer base types*)


def Check(s, msg):
  global sym
  if sym == s:
    sym = ORS.Get()
  else:
    ORS.Mark(msg)


def qualident():
  global sym
  obj = ORB.thisObj()
  sym = ORS.Get();
  if obj == None:
    ORS.Mark("undef")
    obj = dummy
  if (sym == ORS.period) and (obj.class_ == ORB.Mod):
    sym = ORS.Get()
    if sym == ORS.ident:
      obj = ORB.thisimport(obj)
      sym = ORS.Get()
      if obj == None:
        ORS.Mark("undef")
        obj = dummy
    else:
      ORS.Mark("identifier expected")
      obj = dummy
  return obj


def CheckBool(x):
  global sym
  if x.type_.form != ORB.Bool:
    ORS.Mark("not Boolean")
    x.type_ = ORB.boolType


def CheckInt(x):
  global sym
  if x.type_.form != ORB.Int:
    ORS.Mark("not Integer")
    x.type_ = copy(ORB.intType)


def CheckReal(x):
  global sym
  if x.type_.form != ORB.Real:
    ORS.Mark("not Real")
    x.type_ = ORB.realType


def CheckSet(x):
  global sym
  if x.type_.form != ORB.Set:
    ORS.Mark("not Set")
    x.type_ = ORB.setType


def CheckSetVal(x):
  global sym
  if x.type_.form != ORB.Int:
    ORS.Mark("not Int")
    x.type_ = ORB.setType
  elif x.mode == ORB.Const:
    if (x.a < 0) or (x.a >= 32):
      ORS.Mark("invalid set_")


def CheckConst(x):
  global sym
  if x.mode != ORB.Const:
    ORS.Mark("not a constant")
    x.mode = ORB.Const


def CheckReadOnly(x):
  global sym
  if x.rdo:
    ORS.Mark("read-only")


def CheckExport():
  global sym
  if sym == ORS.times:
    expo = True
    sym = ORS.Get();
    if level != 0:
      ORS.Mark("remove asterisk")
  else:
    expo = False
  return expo


def IsExtension(t0, t1):
  global sym
  # (*t1 is an extension of t0*)
  return (t0 == t1) or (t1 != None) and IsExtension(t0, t1.base)


# (* expressions *)

def TypeTest(x, T, guard):
  global sym
  xt = x.type_
  while (xt != T) and (xt != None):
    xt = xt.base
  if xt != T:
    xt = x.type_
    if (xt.form == ORB.Pointer) and (T.form == ORB.Pointer):
      if IsExtension(xt.base, T.base):
        ORG.TypeTest(x, T.base, False, guard)
        x.type_ = T
      else:
        ORS.Mark("not an extension")

    elif (xt.form == ORB.Record) and (T.form == ORB.Record) and (x.mode == ORB.Par):
      if IsExtension(xt, T):
        ORG.TypeTest(x, T, True, guard)
        x.type_ = T
      else:
        ORS.Mark("not an extension")

    else:
      ORS.Mark("incompatible types")

  elif not guard:
    ORG.MakeConstItem(x, ORB.boolType, 1)

  if not guard:
    x.type_ = ORB.boolType


def selector(x):
  global sym
  while ((sym == ORS.lbrak) or (sym == ORS.period) or (sym == ORS.arrow)
         or (sym == ORS.lparen) and (x.type_.form in [ORB.Record, ORB.Pointer])):

    if sym == ORS.lbrak:
      while True:
        sym = ORS.Get()
        y = ORG.Item()
        expression(y)
        if x.type_.form == ORB.Array:
          CheckInt(y)
          ORG.Index(x, y)
          x.type_ = x.type_.base
        else:
          ORS.Mark("not an array")

        if sym != ORS.comma:
          break
      Check(ORS.rbrak, "no ]")

    elif sym == ORS.period:
      sym = ORS.Get();
      if sym == ORS.ident:
        if x.type_.form == ORB.Pointer:
          ORG.DeRef(x)
          x.type_ = x.type_.base
        if x.type_.form == ORB.Record:
          obj = ORB.thisfield(x.type_)
          sym = ORS.Get();
          if obj != None:
            ORG.Field(x, obj)
            x.type_ = obj.type_
          else:
            ORS.Mark("undef")
        else:
          ORS.Mark("not a record")
      else:
        ORS.Mark("ident?")

    elif sym == ORS.arrow:
      sym = ORS.Get()
      if x.type_.form == ORB.Pointer:
        ORG.DeRef(x)
        x.type_ = x.type_.base
      else:
        ORS.Mark("not a pointer")

    elif (sym == ORS.lparen) and (x.type_.form in [ORB.Record, ORB.Pointer]): # (*type_ guard*)
      sym = ORS.Get()
      if sym == ORS.ident:
        obj = qualident()
        if obj.class_ == ORB.Typ:
          TypeTest(x, obj.type_, True)
        else:
          ORS.Mark("guard type_ expected")
      else:
        ORS.Mark("not an identifier")
      Check(ORS.rparen, " ) missing")


def CompTypes(t0, t1, varpar):

  def EqualSignatures(t0, t1):
    com = True;
    if (t0.base == t1.base) and (t0.nofpar == t1.nofpar):
      p0 = t0.dsc
      p1 = t1.dsc;
      while p0 != None:
        if (p0.class_ == p1.class_) and CompTypes(p0.type_, p1.type_, True) and (ord(p0.rdo) == ord(p1.rdo)):
          if p0.type_.form >= ORB.Array:
            com = CompTypes(p0.type_, p1.type_, (p0.class_ == ORB.Par))
          p0 = p0.next
          p1 = p1.next
        else:
          p0 = None
          com = False
    else:
      com = False
    return com

  # (*Compatible Types*)
  return ((t0 == t1)
    or (t0.form == ORB.Array) and (t1.form == ORB.Array) and CompTypes(t0.base, t1.base, varpar)
    or (t0.form == ORB.Pointer) and (t1.form == ORB.Pointer) and IsExtension(t0.base, t1.base)
    or (t0.form == ORB.Record) and (t1.form == ORB.Record) and IsExtension(t0, t1)
    or (t0.form == ORB.Proc) and (t1.form == ORB.Proc) and EqualSignatures(t0, t1)
    or (t0.form in [ORB.Pointer, ORB.Proc]) and (t1.form == ORB.NilTyp)
    or (t0.form == ORB.NilTyp) and (t1.form in [ORB.Pointer, ORB.Proc])
    or not varpar and (t0.form == ORB.Int) and (t1.form == ORB.Int))


def Parameter(par):
  global sym
#  VAR x: ORG.Item; varpar: BOOLEAN;
  x = ORG.Item()
  expression(x);
  if par != None:
    varpar = par.class_ == ORB.Par
    if CompTypes(par.type_, x.type_, varpar):
      if not varpar:
        ORG.ValueParam(x)
      else: # (*par.class_ == Par*)
        if not par.rdo:
          CheckReadOnly(x)
        x = ORG.VarParam(x, par.type_)

    elif not varpar and (par.type_.form == ORB.Int) and (x.type_.form == ORB.Int):
      ORG.ValueParam(x) 

    elif (x.type_.form == ORB.String) and (x.b == 2) and (par.class_ == ORB.Var) and (par.type_.form == ORB.Char):
      ORG.StrToChar(x)
      ORG.ValueParam(x)

    elif ((x.type_.form == ORB.Array) and (par.type_.form == ORB.Array) and
        (x.type_.base.form == par.type_.base.form) and (par.type_.len_ < 0)):
      x = ORG.OpenArrayParam(x)

    elif ((x.type_.form == ORB.String) and (par.class_ == ORB.Par) and (par.type_.form == ORB.Array) and 
        (par.type_.base.form == ORB.Char) and (par.type_.len_ < 0)):
      ORG.StringParam(x)

    elif (par.type_.form == ORB.Array) and (par.type_.base.form == ORB.Int) and (par.type_.size == x.type_.size):
      x = ORG.VarParam(x, par.type_)

    else:
      ORS.Mark("incompatible parameters")


def ParamList(x):
  global sym
#  VAR n: INTEGER; par: ORB.Object;
  par = x.type_.dsc
  n = 0;
  if sym != ORS.rparen:
    Parameter(par)
    n = 1
    while sym <= ORS.comma:
      Check(sym, "comma?")
      if par != None:
        par = par.next
      n += 1
      Parameter(par)
    Check(ORS.rparen, ") missing")
  else:
    sym = ORS.Get();

  if n < x.type_.nofpar:
    ORS.Mark("too few params")
  elif n > x.type_.nofpar:
    ORS.Mark("too many params")


def StandFunc(x, fct, restyp):
  global sym
#  VAR y: ORG.Item; n, npar: LONGINT;
  y = ORG.Item()
  Check(ORS.lparen, "no (");
  npar = fct % 10
  fct = fct / 10
  expression(x)
  n = 1
  while sym == ORS.comma:
    sym = ORS.Get()
    expression(y)
    n +=1
  Check(ORS.rparen, "no )")
  if n == npar:
    if fct == 0: # (*ABS*)
      if x.type_.form in [ORB.Int, ORB.Real]:
        ORG.Abs(x)
        restyp = x.type_
      else:
        ORS.Mark("bad type_")
    elif fct == 1: #(*ODD*)
      CheckInt(x)
      ORG.Odd(x)
    elif fct == 2: #(*FLOOR*)
      CheckReal(x)
      ORG.Floor(x)
    elif fct == 3: #(*FLT*)
      CheckInt(x)
      ORG.Float(x)
    elif fct == 4: #(*ORD*)
      if x.type_.form <= ORB.Proc:
        ORG.Ord(x)
      elif (x.type_.form == ORB.String) and (x.b == 2):
        ORG.StrToChar(x)
      else:
        ORS.Mark("bad type_")

    elif fct == 5: #(*CHR*)
      CheckInt(x)
      ORG.Ord(x)
    elif fct == 6: #(*LEN*)
        if x.type_.form == ORB.Array:
          ORG.Len(x)
        else:
          ORS.Mark("not an array")
    elif fct in {7, 8, 9}: #(*LSL, ASR, ROR*) CheckInt(y);
      if x.type_.form in [ORB.Int, ORB.Set]:
        ORG.Shift(fct-7, x, y)
        restyp = x.type_
      else:
        ORS.Mark("bad type_")
    elif fct == 11: #(*ADC*)
      ORG.ADC(x, y)
    elif fct == 12: #(*SBC*)
      ORG.SBC(x, y)
    elif fct == 13: #(*UML*)
      ORG.UML(x, y)
    elif fct == 14: #(*BIT*)
      CheckInt(x)
      CheckInt(y)
      ORG.Bit(x, y)
    elif fct == 15: #(*REG*)
      CheckConst(x)
      CheckInt(x)
      ORG.Register(x)
    elif fct == 16: #(*VAL*)
      if (x.mode == ORB.Typ) and (x.type_.size <= y.type_.size):
        restyp = x.type_
        x = y
      else:
        ORS.Mark("casting not allowed")

    elif fct == 17: #(*ADR*)
      ORG.Adr(x)
    elif fct == 18: #(*SIZE*)
      if x.mode == ORB.Typ:
        ORG.MakeConstItem(x, ORB.intType, x.type_.size)
      else:
        ORS.Mark("must be a type_")
      END
    elif fct == 19: #(*COND*)
      CheckConst(x)
      CheckInt(x)
      ORG.Condition(x)
    elif fct == 20: #(*H*)
      CheckConst(x)
      CheckInt(x)
      ORG.H(x)

    x.type_ = restyp
  else:
    ORS.Mark("wrong nof params")
  return x


def element(x):
  global sym
  expression(x)
  CheckSetVal(x);
  if sym == ORS.upto:
    sym = ORS.Get()
    y = ORG.Item()
    expression(y)
    CheckSetVal(y)
    ORG.Set(x, y)
  else:
    ORG.Singleton(x)
  x.type_ = ORB.setType


def set_(x):
  global sym
  if sym >= ORS.if_:
    if sym != ORS.rbrace:
      ORS.Mark(" } missing")
    ORG.MakeConstItem(x, ORB.setType, 0) # (*empty set*)
  else:
    y = ORG.Item()
    element(x)
    while (sym < ORS.rparen) or (sym > ORS.rbrace):
      if sym == ORS.comma:
        sym = ORS.Get()
      elif sym != ORS.rbrace:
        ORS.Mark("missing comma")
      element(y)
      ORG.SetOp(ORS.plus, x, y)


def factor(x):
  global sym
  # VAR obj: ORB.Object; rx: LONGINT;
  # (*sync*)
  if (sym < ORS.char) or (sym > ORS.ident):
    ORS.Mark("expression expected");
    while True:
      sym = ORS.Get()
      if (sym >= ORS.char) and (sym <= ORS.ident):
        break

  if sym == ORS.ident:
    obj = qualident();  
    if obj.class_ == ORB.SFunc:
      x = StandFunc(x, obj.val, obj.type_)
    else:
      ORG.MakeItem(x, obj, level)
      selector(x);
      if sym == ORS.lparen:
        sym = ORS.Get()
        rx = ORG.PrepCall(x)
        ParamList(x)
        if (x.type_.form == ORB.Proc) and (x.type_.base.form != ORB.NoTyp):
          ORG.Call(x, rx)
          x.type_ = x.type_.base
        else:
          ORS.Mark("not a function")

  elif sym == ORS.int_:
    ORG.MakeConstItem(x, ORB.intType, ORS.ival)
    sym = ORS.Get()
  elif sym == ORS.real:
    ORG.MakeRealItem(x, ORS.rval)
    sym = ORS.Get()
  elif sym == ORS.char:
    ORG.MakeConstItem(x, ORB.charType, ORS.ival)
    sym = ORS.Get()
  elif sym == ORS.nil:
    sym = ORS.Get()
    ORG.MakeConstItem(x, ORB.nilType, 0)
  elif sym == ORS.string:
    ORG.MakeStringItem(x, ORS.slen)
    sym = ORS.Get()
  elif sym == ORS.lparen:
    sym = ORS.Get()
    expression(x)
    Check(ORS.rparen, "no )")
  elif sym == ORS.lbrace:
    sym = ORS.Get()
    set_(x)
    Check(ORS.rbrace, "no }")
  elif sym == ORS.not_:
    sym = ORS.Get()
    factor(x)
    CheckBool(x)
    ORG.Not(x)
  elif sym == ORS.false:
    sym = ORS.Get()
    ORG.MakeConstItem(x, ORB.boolType, 0)
  elif sym == ORS.true:
    sym = ORS.Get()
    ORG.MakeConstItem(x, ORB.boolType, 1)
  else:
    ORS.Mark("not a factor")
    ORG.MakeItem(x, None, level)


def term(x):
  global sym
  # VAR y: ORG.Item; op, f: INTEGER;
  y = ORG.Item()
  factor(x)
  f = x.type_.form;
  while (sym >= ORS.times) and (sym <= ORS.and_):
    op = sym
    sym = ORS.Get();
    if op == ORS.times:
      if f == ORB.Int:
        factor(y)
        CheckInt(y)
        ORG.MulOp(x, y)
      elif f == ORB.Real:
        factor(y)
        CheckReal(y)
        ORG.RealOp(op, x, y)
      elif f == ORB.Set:
        factor(y)
        CheckSet(y)
        ORG.SetOp(op, x, y)
      else:
        ORS.Mark("bad type_")

    elif (op == ORS.div) or (op == ORS.mod):
      CheckInt(x)
      factor(y)
      CheckInt(y)
      ORG.DivOp(op, x, y)
    elif op == ORS.rdiv:
      if f == ORB.Real:
        factor(y)
        CheckReal(y)
        ORG.RealOp(op, x, y)
      elif f == ORB.Set:
        factor(y)
        CheckSet(y)
        ORG.SetOp(op, x, y)
      else:
        ORS.Mark("bad type_")

    else: # (*op == and*)
      CheckBool(x)
      ORG.And1(x)
      factor(y)
      CheckBool(y)
      ORG.And2(x, y)


def SimpleExpression(x):
  global sym
  # VAR y: ORG.Item; op: INTEGER;
  y = ORG.Item()
  if sym == ORS.minus:
    sym = ORS.Get()
    term(x);
    if x.type_.form in {ORB.Int, ORB.Real, ORB.Set}:
      ORG.Neg(x)
    else:
      CheckInt(x)
  elif sym == ORS.plus:
    sym = ORS.Get()
    term(x);
  else:
    term(x)

  while (sym >= ORS.plus) and (sym <= ORS.or_):
    op = sym
    sym = ORS.Get();
    if op == ORS.or_:
      ORG.Or1(x)
      CheckBool(x)
      term(y)
      CheckBool(y)
      ORG.Or2(x, y)
    elif x.type_.form == ORB.Int:
      term(y)
      CheckInt(y)
      ORG.AddOp(op, x, y)
    elif x.type_.form == ORB.Real:
      term(y)
      CheckReal(y)
      ORG.RealOp(op, x, y)
    else:
      CheckSet(x)
      term(y)
      CheckSet(y)
      ORG.SetOp(op, x, y)


def expression(x):
  global sym
  # VAR y: ORG.Item; obj: ORB.Object; rel, xf, yf: INTEGER;
  y = ORG.Item()
  SimpleExpression(x);
  if (sym >= ORS.eql) and (sym <= ORS.geq):
    rel = sym;
    sym = ORS.Get()
    SimpleExpression(y)
    xf = x.type_.form
    yf = y.type_.form;
    if (CompTypes(x.type_, y.type_, False) or
        (xf == ORB.Pointer) and (yf == ORB.Pointer) and IsExtension(y.type_.base, x.type_.base)):
      if (xf in [ORB.Char, ORB.Int]):
        x, y = ORG.IntRelation(rel, x, y)
      elif xf == ORB.Real:
        x, y = ORG.RealRelation(rel, x, y)
      elif xf == ORB.Set:
        x, y = ORG.SetRelation(rel, x, y)
      elif (xf in [ORB.Pointer, ORB.Proc, ORB.NilTyp]):
        if rel <= ORS.neq:
          x, y = ORG.IntRelation(rel, x, y)
        else:
          ORS.Mark("only == or !=")
      elif (xf == ORB.Array) and (x.type_.base.form == ORB.Char) or (xf == ORB.String):
        x, y = ORG.StringRelation(rel, x, y)
      else:
        ORS.Mark("illegal comparison")

    elif ((xf == ORB.Array) and (x.type_.base.form == ORB.Char) and
          ((yf == ORB.String) or (yf == ORB.Array) and (y.type_.base.form == ORB.Char))
        or (yf == ORB.Array) and (y.type_.base.form == ORB.Char) and (xf == ORB.String)):
      x, y = ORG.StringRelation(rel, x, y)

    elif (xf == ORB.Char) and (yf == ORB.String) and (y.b == 2):
      ORG.StrToChar(y)
      x, y = ORG.IntRelation(rel, x, y)

    elif (yf == ORB.Char) and (xf == ORB.String) and (x.b == 2):
      ORG.StrToChar(x)
      x, y = ORG.IntRelation(rel, x, y)

    else:
      ORS.Mark("illegal comparison")

    x.type_ = ORB.boolType

  elif sym == ORS.in_:
    sym = ORS.Get()
    SimpleExpression(y);
    if (x.type_.form == ORB.Int) and (y.type_.form == ORB.Set):
      ORG.In(x, y)
    else:
      ORS.Mark("illegal operands of IN")

    x.type_ = ORB.boolType

  elif sym == ORS.is_:
    sym = ORS.Get()
    obj = qualident()
    TypeTest(x, obj.type_, False)
    x.type_ = ORB.boolType


# (* statements *)

def StandProc(pno):
  global sym
##  VAR nap, npar: LONGINT; (*nof actual/formal parameters*)
##    x, y, z: ORG.Item;
  Check(ORS.lparen, "no (");
  npar = pno % 10
  pno = pno / 10
  x = ORG.Item()
  y = ORG.Item()
  z = ORG.Item()
  expression(x)
  nap = 1;
  if sym == ORS.comma:
    sym = ORS.Get()
    expression(y)
    nap = 2
    z.type_ = ORB.noType
    while sym == ORS.comma:
      sym = ORS.Get()
      expression(z)
      nap += 1
  else:
    y.type_ = ORB.noType

  Check(ORS.rparen, "no )");
  if (npar == nap) or (pno in [0, 1]): 
    if pno in {0, 1}: # (*INC, DEC*)
      CheckInt(x)
      CheckReadOnly(x);
      if y.type_ != ORB.noType:
        CheckInt(y)
      ORG.Increment(pno, x, y)
    elif pno in {2, 3}: # (*INCL, EXCL*)
      CheckSet(x)
      CheckReadOnly(x)
      CheckInt(y)
      ORG.Include(pno-2, x, y)
    elif pno == 4:
      CheckBool(x)
      ORG.Assert(x)
    elif pno == 5: # (*NEW*)
      CheckReadOnly(x);
      if (x.type_.form == ORB.Pointer) and (x.type_.base.form == ORB.Record):
        ORG.New(x)
      else:
        ORS.Mark("not a pointer to record")
    elif pno == 6:
      CheckReal(x)
      CheckInt(y)
      CheckReadOnly(x)
      ORG.Pack(x, y)
    elif pno == 7:
      CheckReal(x)
      CheckInt(y)
      CheckReadOnly(x)
      ORG.Unpk(x, y)
    elif pno == 8:
      if x.type_.form <= ORB.Set:
        ORG.Led(x)
      else:
        ORS.Mark("bad type_")
    elif pno == 10:
      CheckInt(x)
      ORG.Get(x, y)
    elif pno == 11:
      CheckInt(x)
      ORG.Put(x, y)
    elif pno == 12:
      CheckInt(x)
      CheckInt(y)
      CheckInt(z)
      ORG.Copy(x, y, z)
    elif pno == 13:
      CheckConst(x)
      CheckInt(x)
      ORG.LDPSR(x)
    elif pno == 14:
      CheckInt(x)
      ORG.LDREG(x, y)

  else:
    ORS.Mark("wrong nof parameters")


def StatSequence():
  global sym
##  VAR obj: ORB.Object;
##    orgtype: ORB.Type; (*original type_ of case var*)
##    x, y, z, w: ORG.Item;
##    L0, L1, rx: LONGINT;
  x = ORG.Item()
  y = ORG.Item()
  z = ORG.Item()
  w = ORG.Item()

  def TypeCase(obj, x):
  #  VAR typobj: ORB.Object;
    if sym == ORS.ident:
      typobj = qualident()
      ORG.MakeItem(x, obj, level)
      if typobj.class_ != ORB.Typ:
        ORS.Mark("not a type_")
      TypeTest(x, typobj.type_, False)
      obj.type_ = typobj.type_;
      ORG.CFJump(x)
      Check(ORS.colon, ": expected")
      StatSequence()
    else:
      ORG.CFJump(x)
      ORS.Mark("type_ id_ expected")

  while True: # (*sync*)
    obj = None
    if not ((sym == ORS.ident) or (sym >= ORS.if_) and (sym <= ORS.for_) or (sym >= ORS.semicolon)):
      ORS.Mark("statement expected");
      while True:
        sym = ORS.Get()
        if (sym == ORS.ident) or (sym >= ORS.if_):
          break
    if sym == ORS.ident:
      obj = qualident()
      ORG.MakeItem(x, obj, level);
      if x.mode == ORB.SProc:
        StandProc(obj.val)
      else:
        selector(x);
        if sym == ORS.becomes: # (*assignment*)
          sym = ORS.Get()
          CheckReadOnly(x)
          expression(y);
          if CompTypes(x.type_, y.type_, False) or (x.type_.form == ORB.Int) and (y.type_.form == ORB.Int):
            if (x.type_.form <= ORB.Pointer) or (x.type_.form == ORB.Proc):
              ORG.Store(x, y)
            elif y.type_.size != 0:
              x, y = ORG.StoreStruct(x, y)
          elif (x.type_.form == ORB.Char) and (y.type_.form == ORB.String) and (y.b == 2):
            ORG.StrToChar(y)
            ORG.Store(x, y)
          elif (x.type_.form == ORB.Array) and (x.type_.base.form == ORB.Char) and (y.type_.form == ORB.String):
            x, y = ORG.CopyString(y, x)
          else:
            ORS.Mark("illegal assignment")
        elif sym == ORS.eql:
          ORS.Mark("should be :=")
          sym = ORS.Get()
          expression(y)
        elif sym == ORS.lparen: # (*procedure call*)
          sym = ORS.Get()
          rx = ORG.PrepCall(x)
          ParamList(x);
          if (x.type_.form == ORB.Proc) and (x.type_.base.form == ORB.NoTyp):
            ORG.Call(x, rx)
          else:
            ORS.Mark("not a procedure")

        elif x.type_.form == ORB.Proc: # (*procedure call without parameters*)
          if x.type_.nofpar > 0:
            ORS.Mark("missing parameters")
          if x.type_.base.form == ORB.NoTyp:
            rx = ORG.PrepCall(x)
            ORG.Call(x, rx)
          else:
            ORS.Mark("not a procedure")
        elif x.mode == ORB.Typ:
          ORS.Mark("illegal assignment")
        else:
          ORS.Mark("not a procedure")

    elif sym == ORS.if_:
      sym = ORS.Get()
      expression(x)
      CheckBool(x)
      ORG.CFJump(x)
      Check(ORS.then, "no then")
      StatSequence()
      L0 = 0
      while sym == ORS.elsif:
        sym = ORS.Get()
        L0 = ORG.FJump(L0)
        ORG.Fixup(x)
        expression(x)
        CheckBool(x)
        ORG.CFJump(x)
        Check(ORS.then, "no then")
        StatSequence()

      if sym == ORS.else_:
        sym = ORS.Get();
        L0 = ORG.FJump(L0);
        ORG.Fixup(x);
        StatSequence()

      else:
        ORG.Fixup(x)

      ORG.FixLink(L0)
      Check(ORS.end, "no END")

    elif sym == ORS.while_:
      sym = ORS.Get()
      L0 = ORG.Here()
      expression(x)
      CheckBool(x)
      ORG.CFJump(x)
      Check(ORS.do, "no:")
      StatSequence()
      ORG.BJump(L0)
      while sym == ORS.elsif:
        sym = ORS.Get()
        ORG.Fixup(x)
        expression(x)
        CheckBool(x)
        ORG.CFJump(x)
        Check(ORS.do, "no:")
        StatSequence()
        ORG.BJump(L0)

      ORG.Fixup(x)
      Check(ORS.end, "no END")

    elif sym == ORS.repeat:
      sym = ORS.Get()
      L0 = ORG.Here()
      StatSequence()
      if sym == ORS.until:
        sym = ORS.Get()
        expression(x)
        CheckBool(x)
        ORG.CBJump(x, L0)
      else:
        ORS.Mark("missing UNTIL")

    elif sym == ORS.for_:
      sym = ORS.Get()
      if sym == ORS.ident:
        obj = qualident()
        ORG.MakeItem(x, obj, level)
        CheckInt(x)
        CheckReadOnly(x);
        if sym == ORS.becomes:
          sym = ORS.Get()
          expression(y)
          CheckInt(y)
          ORG.For0(x, y)
          L0 = ORG.Here();
          Check(ORS.to, "no TO")
          expression(z)
          CheckInt(z)
          obj.rdo = True;
          if sym == ORS.by:
            sym = ORS.Get()
            expression(w)
            CheckConst(w)
            CheckInt(w)
          else:
            ORG.MakeConstItem(w, ORB.intType, 1)

          Check(ORS.do, "no:")
          x, y, z, w, L1 = ORG.For1(x, y, z, w);
          StatSequence()
          Check(ORS.end, "no END");
          ORG.For2(x, y, w)
          ORG.BJump(L0)
          ORG.FixLink(L1)
          obj.rdo = False
        else:
          ORS.Mark(":= expected")
      else:
        ORS.Mark("identifier expected")

    elif sym == ORS.case:
      sym = ORS.Get();
      if sym == ORS.ident:
        obj = qualident()
        orgtype = obj.type_;
        if not ((orgtype.form == ORB.Pointer) or (orgtype.form == ORB.Record) and (obj.class_ == ORB.Par)):
          ORS.Mark("bad case var")

        Check(ORS.of, "OF expected")
        TypeCase(obj, x)
        L0 = 0;
        while sym == ORS.bar:
          sym = ORS.Get()
          L0 = ORG.FJump(L0)
          ORG.Fixup(x)
          obj.type_ = orgtype
          TypeCase(obj, x)

        ORG.Fixup(x)
        ORG.FixLink(L0)
        obj.type_ = orgtype
      else:
        ORS.Mark("ident expected")

      Check(ORS.end, "no END")

    ORG.CheckRegs()
    if sym == ORS.semicolon:
      sym = ORS.Get()
    elif sym < ORS.semicolon:
      ORS.Mark("missing semicolon?")

    if sym > ORS.semicolon:
      break


# (* Types and declarations *)

def IdentList(class_):
  global sym
  # VAR obj: ORB.Object;
  if sym == ORS.ident:
    first = ORB.NewObj(''.join(ORS.id_), class_)
    sym = ORS.Get()
    first.expo = CheckExport()
    while sym == ORS.comma:
      sym = ORS.Get();
      if sym == ORS.ident:
        obj = ORB.NewObj(''.join(ORS.id_), class_)
        sym = ORS.Get()
        obj.expo = CheckExport()
      else:
        ORS.Mark("ident?")

    if sym == ORS.colon:
      sym = ORS.Get()
    else:
      ORS.Mark(":?")
  else:
    first = None
  return first


def ArrayType(type_):
  global sym
  # VAR x: ORG.Item; typ: ORB.Type; len_: LONGINT;
  typ = ORB.Type()
  typ.form = ORB.NoTyp
  if sym == ORS.of: # (*dynamic array*)
    len_ = -1
  else:
    x = ORG.Item()
    expression(x)
    if (x.mode == ORB.Const) and (x.type_.form == ORB.Int) and (x.a >= 0):
      len_ = x.a
    else:
      len_ = 0
      ORS.Mark("not a valid length")

  if sym == ORS.of:
    sym = ORS.Get()
    typ.base = Type(typ.base)
    if (typ.base.form == ORB.Array) and (typ.base.len_ < 0):
      ORS.Mark("dyn array not allowed")
  elif sym == ORS.comma:
    sym = ORS.Get()
    typ.base = ArrayType(typ.base)
  else:
    ORS.Mark("missing OF")
    typ.base = ORB.intType

  if len_ >= 0:
    typ.size = len_ * typ.base.size
  else:
    typ.size = 2*ORG.WordSize # (*array desc*)
  typ.form = ORB.Array
  typ.len_ = len_
  type_ = typ
  return type_


def RecordType(type_):
  global sym
##  VAR obj, obj0, new, bot, base: ORB.Object;
##    typ, tp: ORB.Type;
##    offset, off, n: LONGINT;
  typ = ORB.Type()
  typ.form = ORB.NoTyp
  typ.base = None
  typ.mno = level
  typ.nofpar = 0
  offset = 0
  bot = None;
  if sym == ORS.lparen:
    sym = ORS.Get() # (*record extension*)
    if sym == ORS.ident:
      base = qualident()
      if base.class_ == ORB.Typ:
        if base.type_.form == ORB.Record:
          typ.base = base.type_
        else:
          typ.base = ORB.intType
          ORS.Mark("invalid extension")

        typ.nofpar = typ.base.nofpar + 1 # (*"nofpar" here abused for extension level*)
        bot = typ.base.dsc
        offset = typ.base.size
      else:
        ORS.Mark("type_ expected")
    else:
      ORS.Mark("ident expected")

    Check(ORS.rparen, "no )")

  while sym == ORS.ident: # (*fields*)
    n = 0
    obj = bot
    while sym == ORS.ident:
      obj0 = obj
      while (obj0 != None) and (obj0.name != ORS.id_):
        obj0 = obj0.next
      if obj0 != None:
        ORS.Mark("mult def")
      new = ORB.Object()
      new.name = ORS.CopyId()
      new.class_ = ORB.Fld
      new.next = obj
      obj = new
      n += 1
      sym = ORS.Get()
      new.expo = CheckExport()
      if (sym != ORS.comma) and (sym != ORS.colon):
        ORS.Mark("comma expected")
      elif sym == ORS.comma:
        sym = ORS.Get()

    Check(ORS.colon, "colon expected")
    tp = ORB.Type()
    tp = Type(tp)
    if (tp.form == ORB.Array) and (tp.len_ < 0):
      ORS.Mark("dyn array not allowed")
    if tp.size > 1:
      offset = (offset+3) / 4 * 4
    offset = offset + n * tp.size
    off = offset
    obj0 = obj
    while obj0 != bot:
      obj0.type_ = tp
      obj0.lev = 0
      off = off - tp.size
      obj0.val = off
      obj0 = obj0.next
    bot = obj
    if sym == ORS.semicolon:
      sym = ORS.Get()
    elif sym != ORS.end:
      ORS.Mark(" ; or END")

  typ.form = ORB.Record
  typ.dsc = bot
  typ.size = offset
  type_ = typ
  return type_


def FPSection(adr, nofpar):
  global sym
##  VAR obj, first: ORB.Object; tp: ORB.Type;
##    parsize: LONGINT; cl: INTEGER; rdo: BOOLEAN;
  if sym == ORS.var:
    sym = ORS.Get()
    cl = ORB.Par
  else:
    cl = ORB.Var
  first = IdentList(cl)
  tp = FormalType(0)
  rdo = False;
  if (cl == ORB.Var) and (tp.form >= ORB.Array):
    cl = ORB.Par
    rdo = True

  if (tp.form == ORB.Array) and (tp.len_ < 0) or (tp.form == ORB.Record):
    parsize = 2*ORG.WordSize # (*open array or record, needs second word for length or type_ tag*)
  else:
    parsize = ORG.WordSize

  obj = first;
  while obj != None:
    nofpar += 1
    obj.class_ = cl
    obj.type_ = tp
    obj.rdo = rdo
    obj.lev = level
    obj.val = adr
    adr = adr + parsize
    obj = obj.next

  if adr >= 52:
    ORS.Mark("too many parameters")

  return adr, nofpar

def ProcedureType(ptype, parblksize):
  global sym
  # VAR obj: ORB.Object; size: LONGINT; nofpar: INTEGER;
  ptype.base = ORB.noType
  size = parblksize
  nofpar = 0
  ptype.dsc = None
  if sym == ORS.lparen:
    sym = ORS.Get()
    if sym == ORS.rparen:
      sym = ORS.Get()
    else:
      size, nofpar = FPSection(size, nofpar)
      while sym == ORS.semicolon:
        sym = ORS.Get()
        size, nofpar = FPSection(size, nofpar)
      Check(ORS.rparen, "no )")

    ptype.nofpar = nofpar
    parblksize = size
    if sym == ORS.colon: # (*function*)
      sym = ORS.Get()
      if sym == ORS.ident:
        obj = qualident()
        if (obj.class_ == ORB.Typ) and (obj.type_.form in (
          range(ORB.Byte, ORB.Pointer+1) + [ORB.Proc]
          )
                                        ):
          ptype.base = obj.type_
        else:
          ORS.Mark("illegal function type_")

      else:
        ORS.Mark("type_ identifier expected")
  return parblksize


def FormalType(dim):
  global sym
  # VAR obj: ORB.Object; dmy: LONGINT;
  if sym == ORS.ident:
    obj = qualident();
    if obj.class_ == ORB.Typ:
      typ = obj.type_
    else:
      ORS.Mark("not a type_")
      typ = ORB.intType
  elif sym == ORS.array:
    sym = ORS.Get()
    Check(ORS.of, "OF ?");
    if dim >= 1:
      ORS.Mark("multi-dimensional open arrays not implemented")
    typ = ORB.Type()
    typ.form = ORB.Array
    typ.len_ = -1
    typ.size = 2*ORG.WordSize; 
    typ.base = FormalType(dim+1)
  elif sym == ORS.procedure:
    sym = ORS.Get()
    ORB.OpenScope()
    typ = ORB.Type()
    typ.form = ORB.Proc
    typ.size = ORG.WordSize
    ProcedureType(typ, 0)
    typ.dsc = ORB.topScope.next
    ORB.CloseScope()
  else:
    ORS.Mark("identifier expected")
    typ = ORB.noType
  return typ


def Type(type_):
  global sym, pbsList
  # VAR dmy: LONGINT; obj: ORB.Object; ptbase: PtrBase;
  type_ = copy(ORB.intType) # (*sync*)
  obj = ORB.Object()
  if (sym != ORS.ident) and (sym < ORS.array):
    ORS.Mark("not a type_")
    while True:
      sym = ORS.Get()
      if (sym == ORS.ident) or (sym >= ORS.array):
        break

  if sym == ORS.ident:
    obj = qualident()
    if obj.class_ == ORB.Typ:
      if (obj.type_ != None) and (obj.type_.form != ORB.NoTyp):
        type_ = obj.type_
    else:
      ORS.Mark("not a type_ or undefined")

  elif sym == ORS.array:
    sym = ORS.Get()
    type_ = ArrayType(type_)

  elif sym == ORS.record:
    sym = ORS.Get()
    type_ = RecordType(type_)
    Check(ORS.end, "no END")

  elif sym == ORS.pointer:
    sym = ORS.Get()
    Check(ORS.to, "no TO");
    type_ = ORB.Type()
    type_.form = ORB.Pointer
    type_.size = ORG.WordSize
    type_.base = ORB.intType;
    if sym == ORS.ident:
      obj = ORB.thisObj()
      sym = ORS.Get();
      if obj != None:
        if (obj.class_ == ORB.Typ) and (obj.type_.form in {ORB.Record, ORB.NoTyp}):
          type_.base = obj.type_
        else:
          ORS.Mark("no valid base type_")

      ptbase = PtrBase()
      ptbase.name = ORS.CopyId()
      ptbase.type_ = type_
      ptbase.next = pbsList
      pbsList = ptbase
    else:
      type_.base = Type(type_.base)
      if type_.base.form != ORB.Record:
        ORS.Mark("must point to record")

  elif sym == ORS.procedure:
    sym = ORS.Get()
    ORB.OpenScope()
    type_ = ORB.Type()
    type_.form = ORB.Proc
    type_.size = ORG.WordSize
    ProcedureType(type_, 0)
    type_.dsc = ORB.topScope.next
    ORB.CloseScope()
  else:
    ORS.Mark("illegal type_")
  return type_


def Declarations(varsize):
  global sym, id_, exno, pbsList
##  VAR obj, first: ORB.Object;
##    x: ORG.Item; tp: ORB.Type; ptbase: PtrBase;
##    expo: BOOLEAN; id_: ORS.Ident;
  # (*sync*)
  x = ORG.Item()
  obj = ORB.Object()
  tp = ORB.Type()
  pbsList = None
  if (sym < ORS.const) and (sym != ORS.end):
    ORS.Mark("declaration?");
    while True:
      sym = ORS.Get()
      if (sym >= ORS.const) or (sym == ORS.end):
        break

  if sym == ORS.const:
    sym = ORS.Get();
    while sym == ORS.ident:
      id_ = ORS.CopyId()
      sym = ORS.Get()
      expo = CheckExport()
      if sym == ORS.eql:
        sym = ORS.Get()
      else:
        ORS.Mark("= ?")
      expression(x)
      if (x.type_.form == ORB.String) and (x.b == 2):
        ORG.StrToChar(x)
      obj = ORB.NewObj(id_, ORB.Const)
      obj.expo = expo;
      if x.mode == ORB.Const:
        obj.val = x.a
        obj.lev = x.b
        obj.type_ = x.type_
      else:
        ORS.Mark("expression not constant")
        obj.type_ = ORB.intType

      Check(ORS.semicolon, "; missing")

  if sym == ORS.type_:
    sym = ORS.Get()
    while sym == ORS.ident:
      id_ = ORS.CopyId()
      sym = ORS.Get()
      expo = CheckExport()
      if sym == ORS.eql:
        sym = ORS.Get()
      else:
        ORS.Mark("=?")
      tp = Type(tp)
      obj = ORB.NewObj(id_, ORB.Typ)
      obj.type_ = tp
      obj.expo = expo
      obj.lev = level
      tp.typobj = obj;
      if expo and (obj.type_.form == ORB.Record):
        obj.exno = exno
        exno += 1
      else:
        obj.exno = 0
      if tp.form == ORB.Record:
        ptbase = pbsList; # (*check whether this is base of a pointer type_; search and fixup*)
        while ptbase != None:
          if obj.name == ptbase.name:
            if ptbase.type_.base == ORB.intType:
              ptbase.type_.base = obj.type_
            else:
              ORS.Mark("recursive record?")

          ptbase = ptbase.next

        tp.len_ = dc;
        if level == 0:
          ORG.BuildTD(tp, dc) # (*type_ descriptor; len_ used as its address*)

      Check(ORS.semicolon, "; missing")

  if sym == ORS.var:
    sym = ORS.Get()
    while sym == ORS.ident:
      first = IdentList(ORB.Var)
      tp = Type(tp)
      obj = first
      while obj != None:
        obj.type_ = tp
        obj.lev = level;
        if tp.size > 1:
          varsize = (varsize + 3) / 4 * 4 # (*align*)
        obj.val = varsize
        varsize = varsize + obj.type_.size;
        if obj.expo:
          obj.exno = exno
          exno += 1
        obj = obj.next

      Check(ORS.semicolon, "; missing")

  varsize = (varsize + 3) / 4 * 4;
  ptbase = pbsList
  while ptbase != None:
    if ptbase.type_.base.form == ORB.Int:
      ORS.Mark("undefined pointer base of")
    ptbase = ptbase.next

  if (sym >= ORS.const) and (sym <= ORS.var):
    ORS.Mark("declaration in bad order")
  return varsize


def ProcedureDecl():
  global sym, exno, level
##  VAR proc: ORB.Object;
##    type_: ORB.Type;
##    procid: ORS.Ident;
##    x: ORG.Item;
##    locblksize, parblksize, L: LONGINT;
##    int_: BOOLEAN;

  int_ = False
  x = ORG.Item()
  sym = ORS.Get()
  if sym == ORS.times:
    sym = ORS.Get()
    int_ = True
  if sym == ORS.ident:
    procid = ORS.CopyId()
    sym = ORS.Get();
    # (*Texts.WriteLn(W); Texts.WriteString(W, procid); Texts.WriteInt(W, ORG.Here(), 7);*)
    proc = ORB.NewObj(''.join(ORS.id_), ORB.Const)
    parblksize = 4;
    type_ = ORB.Type()
    type_.form = ORB.Proc
    type_.size = ORG.WordSize
    proc.type_ = type_;
    proc.expo = CheckExport()
    if proc.expo:
      proc.exno = exno
      exno += 1
    ORB.OpenScope()
    level += 1
    proc.val = -1
    type_.base = ORB.noType
    parblksize = ProcedureType(type_, parblksize) # (*formal parameter list*)
    Check(ORS.semicolon, "no ;")
    locblksize = parblksize
    locblksize = Declarations(locblksize)
    proc.val = ORG.Here() * 4
    proc.type_.dsc = ORB.topScope.next
    if sym == ORS.procedure:
      L = 0
      L = ORG.FJump(L);
      while True:
        ProcedureDecl()
        Check(ORS.semicolon, "no ;")
        if sym != ORS.procedure:
          break
      ORG.FixLink(L)
      proc.val = ORG.Here() * 4
      proc.type_.dsc = ORB.topScope.next

    ORG.Enter(parblksize, locblksize, int_);
    if sym == ORS.begin:
      sym = ORS.Get()
      StatSequence()

    if sym == ORS.return_:
      sym = ORS.Get()
      expression(x)
      if type_.base == ORB.noType:
        ORS.Mark("this is not a function")
      elif not CompTypes(type_.base, x.type_, False):
        ORS.Mark("wrong result type_")

    elif type_.base.form != ORB.NoTyp:
      ORS.Mark("function without result")
      type_.base = ORB.noType

    ORG.Return(type_.base.form, x, locblksize, int_);
    ORB.CloseScope()
    level -= 1
    Check(ORS.end, "no END");
    if sym == ORS.ident:
      if ''.join(ORS.id_) != procid:
        ORS.Mark("no match")
      sym = ORS.Get()
    else:
      ORS.Mark("no proc id_")

  int_ = False


def Module():
  global sym, modid
##  VAR key: LONGINT;
##    obj: ORB.Object;
##    impid, impid1: ORS.Ident;
  print "  compiling ",
  sym = ORS.Get();
  if sym == ORS.module:
    sym = ORS.Get();
    if sym == ORS.times:
      version = 0
      print "*",
      sym = ORS.Get()
    else:
      version = 1
    ORB.Init()
    ORB.OpenScope()
    if sym == ORS.ident:
      modid = ORS.CopyId()
      sym = ORS.Get();
      print modid,
    else:
      ORS.Mark("identifier expected")

    Check(ORS.semicolon, "no ;")
    level = 0
    dc = 0
    exno = 1
    key = 0;
    if sym == ORS.import_:
      sym = ORS.Get()
      while sym == ORS.ident:
        impid = ORS.CopyId()
        sym = ORS.Get();
        if sym == ORS.becomes:
          sym = ORS.Get();
          if sym == ORS.ident:
            impid1 = ORS.CopyId()
            sym = ORS.Get()
          else:
            ORS.Mark("id_ expected")

        else:
          impid1 = impid

        ORB.Import(impid, impid1)

        if sym == ORS.comma:
          sym = ORS.Get()
        elif sym == ORS.ident:
          ORS.Mark("comma missing")

      Check(ORS.semicolon, "no ;")

    obj = ORB.topScope.next;
    ORG.Open(version)
    dc = Declarations(dc)
    ORG.SetDataSize((dc + 3) / 4 * 4);
    while sym == ORS.procedure:
      ProcedureDecl()
      Check(ORS.semicolon, "no ;")
    ORG.Header()
    if sym == ORS.begin:
      sym = ORS.Get()
      StatSequence()
    Check(ORS.end, "no END")
    if sym == ORS.ident:
      if ''.join(ORS.id_) != modid:
        ORS.Mark("no match")
      sym = ORS.Get()
    else:
      ORS.Mark("identifier missing")

    if sym != ORS.period:
      ORS.Mark("period missing")
    if ORS.errcnt == 0:
      ORB.Export(modid, newSF, key);
      if newSF:
        print
        print "new symbol file "

    if ORS.errcnt == 0:
      ORG.Close(modid, key, exno)
      print
      print "compilation done ", ORG.pc, dc,
    else:
      print
      print "compilation FAILED"

    print
    ORB.CloseScope()
    pbsList = None
  else:
    ORS.Mark("must start with MODULE")


def Compile(T, beg=0):
  ORS.Init(T, beg);
  Module()


print "OR Compiler  5.11.2013"
dummy = ORB.Object()
dummy.class_ = ORB.Var
dummy.type_ = copy(ORB.intType)
