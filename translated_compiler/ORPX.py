##!=!=MODULE ORP; (*N. Wirth 1.7.97 / 5.11.2013  Oberon compiler for RISC in Oberon-07*)
##!=!=  IMPORT Texts, Oberon, ORS, ORB, ORG;
##!=!=  (*Author: Niklaus Wirth, 2011.
##!=!=    Parser of Oberon-RISC compiler. Uses Scanner ORS to obtain symbols (tokens),
##!=!=    ORB for definition of data structures and for handling import and export, and
##!=!=    ORG to produce binary code. ORP performs type_ checking and data allocation.
##!=!=    Parser is target-independent, except for part of the handling of allocations.*)
##!=!=

TYPE PtrBase == POINTER TO PtrBaseDesc;
  PtrBaseDesc == RECORD  (*list of names of pointer base types*)
    name: ORS.Ident; type_: ORB.Type; next: PtrBase
  END ;

VAR

sym = 0 #  (*last symbol read*)
  dc: LONGINT;    (*data counter*)
  level, exno, version: INTEGER;
  newSF: BOOLEAN;  (*option flag*)
  expression: def (x);  (*to avoid forward reference*)
  Type: def (VAR type_: ORB.Type);
  FormalType: def (VAR typ: ORB.Type; dim: INTEGER);
  modid: ORS.Ident;
  pbsList: PtrBase;   (*list of names of pointer base types*)
  dummy: ORB.Object;
  W: Texts.Writer;


def Check(s, msg):
  if sym == s:
    ORS.Get(sym)
  else:
    ORS.Mark(msg)


def qualident(obj):
  obj = ORB.thisObj()
  ORS.Get(sym);
  if obj == None:
    ORS.Mark("undef")
    obj = dummy
  if (sym == ORS.period) and (obj.class_ == ORB.Mod):
    ORS.Get(sym)
    if sym == ORS.ident:
      obj = ORB.thisimport(obj)
      ORS.Get(sym)
      if obj == None:
        ORS.Mark("undef")
        obj = dummy
    else:
      ORS.Mark("identifier expected")
      obj = dummy


def CheckBool(x):
  if x.type_.form != ORB.Bool:
    ORS.Mark("not Boolean")
    x.type_ = ORB.boolType


def CheckInt(x);
  if x.type_.form != ORB.Int:
    ORS.Mark("not Integer")
    x.type_ = ORB.intType


def CheckReal(x);
  if x.type_.form != ORB.Real:
    ORS.Mark("not Real")
    x.type_ = ORB.realType


def CheckSet(x);
  if x.type_.form != ORB.Set:
    ORS.Mark("not Set")
    x.type_ = ORB.setType


def CheckSetVal(x):
  if x.type_.form != ORB.Int:
    ORS.Mark("not Int")
    x.type_ = ORB.setType
  elif x.mode == ORB.Const:
    if (x.a < 0) or (x.a >= 32):
      ORS.Mark("invalid set")


def CheckConst(x):
  if x.mode != ORB.Const:
    ORS.Mark("not a constant")
    x.mode = ORB.Const


def CheckReadOnly(x):
  if x.rdo:
    ORS.Mark("read-only")


def CheckExport(VAR expo: BOOLEAN);
  if sym == ORS.times:
    expo = True
    ORS.Get(sym);
    if level != 0:
      ORS.Mark("remove asterisk")
  else:
    expo = False


def IsExtension(t0, t1: ORB.Type):
  # (*t1 is an extension of t0*)
  return (t0 == t1) or (t1 != None) and IsExtension(t0, t1.base)


# (* expressions *)

def TypeTest(VAR x: ORG.Item; T: ORB.Type; guard: BOOLEAN);
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
  VAR y: ORG.Item; obj: ORB.Object;
BEGIN
  while (sym == ORS.lbrak) or (sym == ORS.period) or (sym == ORS.arrow)
      or (sym == ORS.lparen) and (x.type_.form IN {ORB.Record, ORB.Pointer}):
    if sym == ORS.lbrak:
      REPEAT ORS.Get(sym); expression(y);
        if x.type_.form == ORB.Array:
          CheckInt(y); ORG.Index(x, y); x.type_ = x.type_.base
        else: ORS.Mark("not an array")
        END
      UNTIL sym != ORS.comma;
      Check(ORS.rbrak, "no ]")
    elif sym == ORS.period: ORS.Get(sym);
      if sym == ORS.ident:
        if x.type_.form == ORB.Pointer: ORG.DeRef(x); x.type_ = x.type_.base END ;
        if x.type_.form == ORB.Record:
          obj = ORB.thisfield(x.type_); ORS.Get(sym);
          if obj != None: ORG.Field(x, obj); x.type_ = obj.type_
          else: ORS.Mark("undef")
          END
        else: ORS.Mark("not a record")
        END
      else: ORS.Mark("ident?")
      END
    elif sym == ORS.arrow:
      ORS.Get(sym);
      if x.type_.form == ORB.Pointer: ORG.DeRef(x); x.type_ = x.type_.base
      else: ORS.Mark("not a pointer")
      END
    elif (sym == ORS.lparen) and (x.type_.form IN {ORB.Record, ORB.Pointer}): (*type_ guard*)
      ORS.Get(sym);
      if sym == ORS.ident:
        qualident(obj);
        if obj.class_ == ORB.Typ: TypeTest(x, obj.type_, True)
        else: ORS.Mark("guard type_ expected")
        END
      else: ORS.Mark("not an identifier")
      END ;
      Check(ORS.rparen, " ) missing")
    END
  END
END selector;

def CompTypes(t0, t1: ORB.Type; varpar: BOOLEAN): BOOLEAN;

  def EqualSignatures(t0, t1: ORB.Type): BOOLEAN;
    VAR p0, p1: ORB.Object; com: BOOLEAN;
  BEGIN com = True;
    if (t0.base == t1.base) and (t0.nofpar == t1.nofpar):
      p0 = t0.dsc; p1 = t1.dsc;
      while p0 != None:
        if (p0.class_ == p1.class_) and CompTypes(p0.type_, p1.type_, True) and (ORD(p0.rdo) == ORD(p1.rdo)):
          if p0.type_.form >= ORB.Array: com = CompTypes(p0.type_, p1.type_, (p0.class_ == ORB.Par)) END ;
          p0 = p0.next; p1 = p1.next
        else: p0 = None; com = False
        END
      END
    else: com = False
    END ;
    return com
  END EqualSignatures;

BEGIN (*Compatible Types*)
  return (t0 == t1)
    or (t0.form == ORB.Array) and (t1.form == ORB.Array) and CompTypes(t0.base, t1.base, varpar)
    or (t0.form == ORB.Pointer) and (t1.form == ORB.Pointer) and IsExtension(t0.base, t1.base)
    or (t0.form == ORB.Record) and (t1.form == ORB.Record) and IsExtension(t0, t1)
    or (t0.form == ORB.Proc) and (t1.form == ORB.Proc) and EqualSignatures(t0, t1)
    or (t0.form IN {ORB.Pointer, ORB.Proc}) and (t1.form == ORB.NilTyp)
    or (t0.form == ORB.NilTyp) and (t1.form IN {ORB.Pointer, ORB.Proc})
    or ~varpar and (t0.form == ORB.Int) and (t1.form == ORB.Int)
END CompTypes;

def Parameter(par: ORB.Object);
  VAR x: ORG.Item; varpar: BOOLEAN;
BEGIN expression(x);
  if par != None:
    varpar = par.class_ == ORB.Par;
    if CompTypes(par.type_, x.type_, varpar):
      if ~varpar: ORG.ValueParam(x)
      else: (*par.class_ == Par*)
        if ~par.rdo: CheckReadOnly(x) END ;
        ORG.VarParam(x, par.type_)
      END
    elif ~varpar and (par.type_.form == ORB.Int) and (x.type_.form == ORB.Int):
      ORG.ValueParam(x) 
    elif (x.type_.form == ORB.String) and (x.b == 2) and (par.class_ == ORB.Var) and (par.type_.form == ORB.Char):
      ORG.StrToChar(x); ORG.ValueParam(x)
    elif (x.type_.form == ORB.Array) and (par.type_.form == ORB.Array) &
        (x.type_.base.form == par.type_.base.form) and (par.type_.len_ < 0):
      ORG.OpenArrayParam(x);
    elif (x.type_.form == ORB.String) and (par.class_ == ORB.Par) and (par.type_.form == ORB.Array) and 
        (par.type_.base.form == ORB.Char) and (par.type_.len_ < 0): ORG.StringParam(x)
    elif (par.type_.form == ORB.Array) and (par.type_.base.form == ORB.Int) and (par.type_.size == x.type_.size):
      ORG.VarParam(x, par.type_)
    else: ORS.Mark("incompatible parameters")
    END
  END
END Parameter;

def ParamList(x):
  VAR n: INTEGER; par: ORB.Object;
BEGIN par = x.type_.dsc; n = 0;
  if sym != ORS.rparen:
    Parameter(par); n = 1;
    while sym <= ORS.comma:
      Check(sym, "comma?");
      if par != None: par = par.next END ;
      INC(n); Parameter(par)
    END ;
    Check(ORS.rparen, ") missing")
  else: ORS.Get(sym);
  END ;
  if n < x.type_.nofpar: ORS.Mark("too few params")
  elif n > x.type_.nofpar: ORS.Mark("too many params")
  END
END ParamList;

def StandFunc(VAR x: ORG.Item; fct: LONGINT; restyp: ORB.Type);
  VAR y: ORG.Item; n, npar: LONGINT;
BEGIN Check(ORS.lparen, "no (");
  npar = fct MOD 10; fct = fct DIV 10; expression(x); n = 1;
  while sym == ORS.comma: ORS.Get(sym); expression(y); INC(n) END ;
  Check(ORS.rparen, "no )");
  if n == npar:
    if fct == 0: (*ABS*)
      if x.type_.form IN {ORB.Int, ORB.Real}: ORG.Abs(x); restyp = x.type_ else: ORS.Mark("bad type_") END
    elif fct == 1: (*ODD*) CheckInt(x); ORG.Odd(x)
    elif fct == 2: (*FLOOR*) CheckReal(x); ORG.Floor(x)
    elif fct == 3: (*FLT*) CheckInt(x); ORG.Float(x)
    elif fct == 4: (*ORD*)
      if x.type_.form <= ORB.Proc: ORG.Ord(x)
      elif (x.type_.form == ORB.String) and (x.b == 2): ORG.StrToChar(x)
      else: ORS.Mark("bad type_")
      END
    elif fct == 5: (*CHR*) CheckInt(x); ORG.Ord(x)
    elif fct == 6: (*LEN*)
        if x.type_.form == ORB.Array: ORG.Len(x) else: ORS.Mark("not an array") END
    elif fct IN {7, 8, 9}: (*LSL, ASR, ROR*) CheckInt(y);
      if x.type_.form IN {ORB.Int, ORB.Set}: ORG.Shift(fct-7, x, y); restyp = x.type_ else: ORS.Mark("bad type_") END
    elif fct == 11: (*ADC*) ORG.ADC(x, y)
    elif fct == 12: (*SBC*) ORG.SBC(x, y)
    elif fct == 13: (*UML*) ORG.UML(x, y)
    elif fct == 14: (*BIT*) CheckInt(x); CheckInt(y); ORG.Bit(x, y)
    elif fct == 15: (*REG*) CheckConst(x); CheckInt(x); ORG.Register(x)
    elif fct == 16: (*VAL*)
      if (x.mode= ORB.Typ) and (x.type_.size <= y.type_.size): restyp = x.type_; x = y
      else: ORS.Mark("casting not allowed")
      END
    elif fct == 17: (*ADR*) ORG.Adr(x)
    elif fct == 18: (*SIZE*)
      if x.mode == ORB.Typ: ORG.MakeConstItem(x, ORB.intType, x.type_.size)
      else: ORS.Mark("must be a type_")
      END
    elif fct == 19: (*COND*) CheckConst(x); CheckInt(x); ORG.Condition(x)
    elif fct == 20: (*H*) CheckConst(x); CheckInt(x); ORG.H(x)
    END ;
    x.type_ = restyp
  else: ORS.Mark("wrong nof params")
  END
END StandFunc;

def element(x):
  VAR y: ORG.Item;
BEGIN expression(x); CheckSetVal(x);
  if sym == ORS.upto: ORS.Get(sym); expression(y); CheckSetVal(y); ORG.Set(x, y)
  else: ORG.Singleton(x)
  END ;
  x.type_ = ORB.setType
END element;

def set(x):
  VAR y: ORG.Item;
BEGIN
  if sym >= ORS.if:
    if sym != ORS.rbrace: ORS.Mark(" } missing") END ;
    ORG.MakeConstItem(x, ORB.setType, 0) (*empty set*)
  else: element(x);
    while (sym < ORS.rparen) or (sym > ORS.rbrace):
      if sym == ORS.comma: ORS.Get(sym)
      elif sym != ORS.rbrace: ORS.Mark("missing comma")
      END ;
      element(y); ORG.SetOp(ORS.plus, x, y)
    END
  END
END set; 

def factor(x):
  VAR obj: ORB.Object; rx: LONGINT;
BEGIN (*sync*)
  if (sym < ORS.char) or (sym > ORS.ident): ORS.Mark("expression expected");
    REPEAT ORS.Get(sym) UNTIL (sym >= ORS.char) and (sym <= ORS.ident)
  END ;
  if sym == ORS.ident:
    qualident(obj);  
    if obj.class_ == ORB.SFunc: StandFunc(x, obj.val, obj.type_)
    else: ORG.MakeItem(x, obj, level); selector(x);
      if sym == ORS.lparen:
        ORS.Get(sym); ORG.PrepCall(x, rx); ParamList(x);
        if (x.type_.form == ORB.Proc) and (x.type_.base.form != ORB.NoTyp):
          ORG.Call(x, rx); x.type_ = x.type_.base
        else: ORS.Mark("not a function")
        END ;
      END
    END
  elif sym == ORS.int_: ORG.MakeConstItem(x, ORB.intType, ORS.ival); ORS.Get(sym)
  elif sym == ORS.real: ORG.MakeRealItem(x, ORS.rval); ORS.Get(sym)
  elif sym == ORS.char: ORG.MakeConstItem(x, ORB.charType, ORS.ival); ORS.Get(sym)
  elif sym == ORS.nil: ORS.Get(sym); ORG.MakeConstItem(x, ORB.nilType, 0)
  elif sym == ORS.string: ORG.MakeStringItem(x, ORS.slen); ORS.Get(sym)
  elif sym == ORS.lparen: ORS.Get(sym); expression(x); Check(ORS.rparen, "no )")
  elif sym == ORS.lbrace: ORS.Get(sym); set(x); Check(ORS.rbrace, "no }")
  elif sym == ORS.not: ORS.Get(sym); factor(x); CheckBool(x); ORG.Not(x)
  elif sym == ORS.false: ORS.Get(sym); ORG.MakeConstItem(x, ORB.boolType, 0)
  elif sym == ORS.true: ORS.Get(sym); ORG.MakeConstItem(x, ORB.boolType, 1)
  else: ORS.Mark("not a factor"); ORG.MakeItem(x, None, level)
  END
END factor;

def term(x):
  VAR y: ORG.Item; op, f: INTEGER;
BEGIN factor(x); f = x.type_.form;
  while (sym >= ORS.times) and (sym <= ORS.and):
    op = sym; ORS.Get(sym);
    if op == ORS.times:
      if f == ORB.Int: factor(y); CheckInt(y); ORG.MulOp(x, y)
      elif f == ORB.Real: factor(y); CheckReal(y); ORG.RealOp(op, x, y)
      elif f == ORB.Set: factor(y); CheckSet(y); ORG.SetOp(op, x, y)
      else: ORS.Mark("bad type_")
      END
    elif (op == ORS.div) or (op == ORS.mod):
      CheckInt(x); factor(y); CheckInt(y); ORG.DivOp(op, x, y)
    elif op == ORS.rdiv:
      if f == ORB.Real: factor(y); CheckReal(y); ORG.RealOp(op, x, y)
      elif f == ORB.Set: factor(y); CheckSet(y); ORG.SetOp(op, x, y)
      else: ORS.Mark("bad type_")
      END
    else: (*op == and*) CheckBool(x); ORG.And1(x); factor(y); CheckBool(y); ORG.And2(x, y)
    END
  END
END term;

def SimpleExpression(x):
  VAR y: ORG.Item; op: INTEGER;
BEGIN
  if sym == ORS.minus: ORS.Get(sym); term(x);
    if x.type_.form IN {ORB.Int, ORB.Real, ORB.Set}: ORG.Neg(x) else: CheckInt(x) END
  elif sym == ORS.plus: ORS.Get(sym); term(x);
  else: term(x)
  END ;
  while (sym >= ORS.plus) and (sym <= ORS.or):
    op = sym; ORS.Get(sym);
    if op == ORS.or: ORG.Or1(x); CheckBool(x); term(y); CheckBool(y); ORG.Or2(x, y)
    elif x.type_.form == ORB.Int: term(y); CheckInt(y); ORG.AddOp(op, x, y)
    elif x.type_.form == ORB.Real: term(y); CheckReal(y); ORG.RealOp(op, x, y)
    else: CheckSet(x); term(y); CheckSet(y); ORG.SetOp(op, x, y)
    END
  END
END SimpleExpression;

def expression0(x):
  VAR y: ORG.Item; obj: ORB.Object; rel, xf, yf: INTEGER;
BEGIN SimpleExpression(x);
  if (sym >= ORS.eql) and (sym <= ORS.geq):
    rel = sym; ORS.Get(sym); SimpleExpression(y); xf = x.type_.form; yf = y.type_.form;
    if CompTypes(x.type_, y.type_, False) or
        (xf == ORB.Pointer) and (yf == ORB.Pointer) and IsExtension(y.type_.base, x.type_.base):
      if (xf IN {ORB.Char, ORB.Int}): ORG.IntRelation(rel, x, y)
      elif xf == ORB.Real: ORG.RealRelation(rel, x, y)
      elif xf == ORB.Set: ORG.SetRelation(rel, x, y)
      elif (xf IN {ORB.Pointer, ORB.Proc, ORB.NilTyp}):
        if rel <= ORS.neq: ORG.IntRelation(rel, x, y) else: ORS.Mark("only == or !=") END
      elif (xf == ORB.Array) and (x.type_.base.form == ORB.Char) or (xf == ORB.String):
        ORG.StringRelation(rel, x, y)
      else: ORS.Mark("illegal comparison")
      END
    elif (xf == ORB.Array) and (x.type_.base.form == ORB.Char) &
          ((yf == ORB.String) or (yf == ORB.Array) and (y.type_.base.form == ORB.Char))
        or (yf == ORB.Array) and (y.type_.base.form == ORB.Char) and (xf == ORB.String):
      ORG.StringRelation(rel, x, y)
    elif (xf == ORB.Char) and (yf == ORB.String) and (y.b == 2):
      ORG.StrToChar(y); ORG.IntRelation(rel, x, y)
    elif (yf == ORB.Char) and (xf == ORB.String) and (x.b == 2):
      ORG.StrToChar(x); ORG.IntRelation(rel, x, y)
    else: ORS.Mark("illegal comparison")
    END ;
    x.type_ = ORB.boolType
  elif sym == ORS.in:
    ORS.Get(sym); SimpleExpression(y);
    if (x.type_.form == ORB.Int) and (y.type_.form == ORB.Set): ORG.In(x, y)
    else: ORS.Mark("illegal operands of IN")
    END ;
    x.type_ = ORB.boolType
  elif sym == ORS.is:
    ORS.Get(sym); qualident(obj); TypeTest(x, obj.type_, False) ;
    x.type_ = ORB.boolType
  END
END expression0;

(* statements *)

def StandProc(pno: LONGINT);
  VAR nap, npar: LONGINT; (*nof actual/formal parameters*)
    x, y, z: ORG.Item;
BEGIN Check(ORS.lparen, "no (");
  npar = pno MOD 10; pno = pno DIV 10; expression(x); nap = 1;
  if sym == ORS.comma:
    ORS.Get(sym); expression(y); nap = 2; z.type_ = ORB.noType;
    while sym == ORS.comma: ORS.Get(sym); expression(z); INC(nap) END
  else: y.type_ = ORB.noType
  END ;
  Check(ORS.rparen, "no )");
  if (npar == nap) or (pno IN {0, 1}): 
    if pno IN {0, 1}: (*INC, DEC*)
      CheckInt(x); CheckReadOnly(x);
      if y.type_ != ORB.noType: CheckInt(y) END ;
      ORG.Increment(pno, x, y)
    elif pno IN {2, 3}: (*INCL, EXCL*)
      CheckSet(x); CheckReadOnly(x); CheckInt(y); ORG.Include(pno-2, x, y)
    elif pno == 4: CheckBool(x); ORG.Assert(x)
    elif pno == 5:(*NEW*) CheckReadOnly(x);
       if (x.type_.form == ORB.Pointer) and (x.type_.base.form == ORB.Record): ORG.New(x)
       else: ORS.Mark("not a pointer to record")
       END
    elif pno == 6: CheckReal(x); CheckInt(y); CheckReadOnly(x); ORG.Pack(x, y)
    elif pno == 7: CheckReal(x); CheckInt(y); CheckReadOnly(x); ORG.Unpk(x, y)
    elif pno == 8:
      if x.type_.form <= ORB.Set: ORG.Led(x) else: ORS.Mark("bad type_") END
    elif pno == 10: CheckInt(x); ORG.Get(x, y)
    elif pno == 11: CheckInt(x); ORG.Put(x, y)
    elif pno == 12: CheckInt(x); CheckInt(y); CheckInt(z); ORG.Copy(x, y, z)
    elif pno == 13: CheckConst(x); CheckInt(x); ORG.LDPSR(x)
    elif pno == 14: CheckInt(x); ORG.LDREG(x, y)
    END
  else: ORS.Mark("wrong nof parameters")
  END
END StandProc;

def StatSequence;
  VAR obj: ORB.Object;
    orgtype: ORB.Type; (*original type_ of case var*)
    x, y, z, w: ORG.Item;
    L0, L1, rx: LONGINT;

  def TypeCase(obj: ORB.Object; VAR x: ORG.Item);
    VAR typobj: ORB.Object;
  BEGIN
    if sym == ORS.ident:
      qualident(typobj); ORG.MakeItem(x, obj, level);
      if typobj.class_ != ORB.Typ: ORS.Mark("not a type_") END ;
      TypeTest(x, typobj.type_, False); obj.type_ = typobj.type_;
      ORG.CFJump(x); Check(ORS.colon, ": expected"); StatSequence
    else: ORG.CFJump(x); ORS.Mark("type_ id_ expected")
    END
   END TypeCase;

BEGIN (* StatSequence *)
  REPEAT (*sync*) obj = None;
    if ~((sym == ORS.ident) or (sym >= ORS.if) and (sym <= ORS.for) or (sym >= ORS.semicolon)):
      ORS.Mark("statement expected");
      REPEAT ORS.Get(sym) UNTIL (sym == ORS.ident) or (sym >= ORS.if)
    END ;
    if sym == ORS.ident:
      qualident(obj); ORG.MakeItem(x, obj, level);
      if x.mode == ORB.SProc: StandProc(obj.val)
      else: selector(x);
        if sym == ORS.becomes: (*assignment*)
          ORS.Get(sym); CheckReadOnly(x); expression(y);
          if CompTypes(x.type_, y.type_, False) or (x.type_.form == ORB.Int) and (y.type_.form == ORB.Int):
            if (x.type_.form <= ORB.Pointer) or (x.type_.form == ORB.Proc): ORG.Store(x, y)
            elif y.type_.size != 0: ORG.StoreStruct(x, y)
            END
          elif (x.type_.form == ORB.Char) and (y.type_.form == ORB.String) and (y.b == 2):
            ORG.StrToChar(y); ORG.Store(x, y)
          elif (x.type_.form == ORB.Array) and (x.type_.base.form == ORB.Char) and 
              (y.type_.form == ORB.String): ORG.CopyString(y, x)
          else: ORS.Mark("illegal assignment")
          END
        elif sym == ORS.eql: ORS.Mark("should be :="); ORS.Get(sym); expression(y)
        elif sym == ORS.lparen: (*procedure call*)
          ORS.Get(sym); ORG.PrepCall(x, rx); ParamList(x);
          if (x.type_.form == ORB.Proc) and (x.type_.base.form == ORB.NoTyp): ORG.Call(x, rx)
          else: ORS.Mark("not a procedure")
          END
        elif x.type_.form == ORB.Proc: (*procedure call without parameters*)
          if x.type_.nofpar > 0: ORS.Mark("missing parameters") END ;
          if x.type_.base.form == ORB.NoTyp: ORG.PrepCall(x, rx); ORG.Call(x, rx) else: ORS.Mark("not a procedure") END
        elif x.mode == ORB.Typ: ORS.Mark("illegal assignment")
        else: ORS.Mark("not a procedure")
        END
      END
    elif sym == ORS.if:
      ORS.Get(sym); expression(x); CheckBool(x); ORG.CFJump(x);
      Check(ORS.then, "no:");
      StatSequence; L0 = 0;
      while sym == ORS.elsif:
        ORS.Get(sym); ORG.FJump(L0); ORG.Fixup(x); expression(x); CheckBool(x);
        ORG.CFJump(x); Check(ORS.then, "no:"); StatSequence
      END ;
      if sym == ORS.else: ORS.Get(sym); ORG.FJump(L0); ORG.Fixup(x); StatSequence
      else: ORG.Fixup(x)
      END ;
      ORG.FixLink(L0); Check(ORS.end, "no END")
    elif sym == ORS.while:
      ORS.Get(sym); L0 = ORG.Here(); expression(x); CheckBool(x); ORG.CFJump(x);
      Check(ORS.do, "no:"); StatSequence; ORG.BJump(L0);
      while sym == ORS.elsif:
        ORS.Get(sym); ORG.Fixup(x); expression(x); CheckBool(x); ORG.CFJump(x);
        Check(ORS.do, "no:"); StatSequence; ORG.BJump(L0)
      END ;
      ORG.Fixup(x); Check(ORS.end, "no END")
    elif sym == ORS.repeat:
      ORS.Get(sym); L0 = ORG.Here(); StatSequence;
      if sym == ORS.until:
        ORS.Get(sym); expression(x); CheckBool(x); ORG.CBJump(x, L0)
      else: ORS.Mark("missing UNTIL")
      END
    elif sym == ORS.for:
      ORS.Get(sym);
      if sym == ORS.ident:
        qualident(obj); ORG.MakeItem(x, obj, level); CheckInt(x); CheckReadOnly(x);
        if sym == ORS.becomes:
          ORS.Get(sym); expression(y); CheckInt(y); ORG.For0(x, y); L0 = ORG.Here();
          Check(ORS.to, "no TO"); expression(z); CheckInt(z); obj.rdo = True;
          if sym == ORS.by: ORS.Get(sym); expression(w); CheckConst(w); CheckInt(w)
          else: ORG.MakeConstItem(w, ORB.intType, 1)
          END ;
          Check(ORS.do, "no:"); ORG.For1(x, y, z, w, L1);
          StatSequence; Check(ORS.end, "no END");
          ORG.For2(x, y, w); ORG.BJump(L0); ORG.FixLink(L1); obj.rdo = False
        else: ORS.Mark(":= expected")
        END
      else: ORS.Mark("identifier expected")
      END
    elif sym == ORS.case:
      ORS.Get(sym);
      if sym == ORS.ident:
        qualident(obj); orgtype = obj.type_;
        if ~((orgtype.form == ORB.Pointer) or (orgtype.form == ORB.Record) and (obj.class_ == ORB.Par)):
          ORS.Mark("bad case var")
        END ;
        Check(ORS.of, "OF expected"); TypeCase(obj, x); L0 = 0;
        while sym == ORS.bar:
          ORS.Get(sym); ORG.FJump(L0); ORG.Fixup(x); obj.type_ = orgtype; TypeCase(obj, x)
        END ;
        ORG.Fixup(x); ORG.FixLink(L0); obj.type_ = orgtype
      else: ORS.Mark("ident expected")
      END ;
      Check(ORS.end, "no END")
    END ;
    ORG.CheckRegs;
    if sym == ORS.semicolon: ORS.Get(sym)
    elif sym < ORS.semicolon: ORS.Mark("missing semicolon?")
    END
  UNTIL sym > ORS.semicolon
END StatSequence;

(* Types and declarations *)

def IdentList(class_: INTEGER; VAR first: ORB.Object);
  VAR obj: ORB.Object;
BEGIN
  if sym == ORS.ident:
    ORB.NewObj(first, ORS.id_, class_); ORS.Get(sym); CheckExport(first.expo);
    while sym == ORS.comma:
      ORS.Get(sym);
      if sym == ORS.ident: ORB.NewObj(obj, ORS.id_, class_); ORS.Get(sym); CheckExport(obj.expo)
      else: ORS.Mark("ident?")
      END
    END;
    if sym == ORS.colon: ORS.Get(sym) else: ORS.Mark(":?") END
  else: first = None
  END
END IdentList;

def ArrayType(VAR type_: ORB.Type);
  VAR x: ORG.Item; typ: ORB.Type; len_: LONGINT;
BEGIN NEW(typ); typ.form = ORB.NoTyp;
  if sym == ORS.of: (*dynamic array*) len_ = -1
  else: expression(x);
    if (x.mode == ORB.Const) and (x.type_.form == ORB.Int) and (x.a >= 0): len_ = x.a
    else: len_ = 0; ORS.Mark("not a valid length")
    END
  END ;
  if sym == ORS.of: ORS.Get(sym); Type(typ.base);
    if (typ.base.form == ORB.Array) and (typ.base.len_ < 0): ORS.Mark("dyn array not allowed") END
  elif sym == ORS.comma: ORS.Get(sym); ArrayType(typ.base)
  else: ORS.Mark("missing OF"); typ.base = ORB.intType
  END ;
  if len_ >= 0: typ.size = len_ * typ.base.size else: typ.size = 2*ORG.WordSize  (*array desc*) END ;
  typ.form = ORB.Array; typ.len_ = len_; type_ = typ
END ArrayType;

def RecordType(VAR type_: ORB.Type);
  VAR obj, obj0, new, bot, base: ORB.Object;
    typ, tp: ORB.Type;
    offset, off, n: LONGINT;
BEGIN NEW(typ); typ.form = ORB.NoTyp; typ.base = None; typ.mno = level; typ.nofpar = 0;
  offset = 0; bot = None;
  if sym == ORS.lparen:
    ORS.Get(sym); (*record extension*)
    if sym == ORS.ident:
      qualident(base);
      if base.class_ == ORB.Typ:
        if base.type_.form == ORB.Record: typ.base = base.type_
        else: typ.base = ORB.intType; ORS.Mark("invalid extension")
        END ;
        typ.nofpar = typ.base.nofpar + 1; (*"nofpar" here abused for extension level*)
        bot = typ.base.dsc; offset = typ.base.size
      else: ORS.Mark("type_ expected")
      END
    else: ORS.Mark("ident expected")
    END ;
    Check(ORS.rparen, "no )")
  END ;
  while sym == ORS.ident:  (*fields*)
    n = 0; obj = bot;
    while sym == ORS.ident:
      obj0 = obj;
      while (obj0 != None) and (obj0.name != ORS.id_): obj0 = obj0.next END ;
      if obj0 != None: ORS.Mark("mult def") END ;
      NEW(new); ORS.CopyId(new.name); new.class_ = ORB.Fld; new.next = obj; obj = new; INC(n);
      ORS.Get(sym); CheckExport(new.expo);
      if (sym != ORS.comma) and (sym != ORS.colon): ORS.Mark("comma expected")
      elif sym == ORS.comma: ORS.Get(sym)
      END
    END ;
    Check(ORS.colon, "colon expected"); Type(tp);
    if (tp.form == ORB.Array) and (tp.len_ < 0): ORS.Mark("dyn array not allowed") END ;
    if tp.size > 1: offset = (offset+3) DIV 4 * 4 END ;
    offset = offset + n * tp.size; off = offset; obj0 = obj;
    while obj0 != bot: obj0.type_ = tp; obj0.lev = 0; off = off - tp.size; obj0.val = off; obj0 = obj0.next END ;
    bot = obj;
    if sym == ORS.semicolon: ORS.Get(sym) elif sym != ORS.end: ORS.Mark(" ; or END") END
  END ;
  typ.form = ORB.Record; typ.dsc = bot; typ.size = offset; type_ = typ
END RecordType;

def FPSection(VAR adr: LONGINT; VAR nofpar: INTEGER);
  VAR obj, first: ORB.Object; tp: ORB.Type;
    parsize: LONGINT; cl: INTEGER; rdo: BOOLEAN;
BEGIN
  if sym == ORS.var: ORS.Get(sym); cl = ORB.Par else: cl = ORB.Var END ;
  IdentList(cl, first); FormalType(tp, 0); rdo = False;
  if (cl == ORB.Var) and (tp.form >= ORB.Array): cl = ORB.Par; rdo = True END ;
  if (tp.form == ORB.Array) and (tp.len_ < 0) or (tp.form == ORB.Record):
    parsize = 2*ORG.WordSize  (*open array or record, needs second word for length or type_ tag*)
  else: parsize = ORG.WordSize
  END ;
  obj = first;
  while obj != None:
    INC(nofpar); obj.class_ = cl; obj.type_ = tp; obj.rdo = rdo; obj.lev = level; obj.val = adr;
    adr = adr + parsize; obj = obj.next
  END ;
  if adr >= 52: ORS.Mark("too many parameters") END
END FPSection;

def ProcedureType(ptype: ORB.Type; VAR parblksize: LONGINT);
  VAR obj: ORB.Object; size: LONGINT; nofpar: INTEGER;
BEGIN ptype.base = ORB.noType; size = parblksize; nofpar = 0; ptype.dsc = None;
  if sym == ORS.lparen:
    ORS.Get(sym);
    if sym == ORS.rparen: ORS.Get(sym)
    else: FPSection(size, nofpar);
      while sym == ORS.semicolon: ORS.Get(sym); FPSection(size, nofpar) END ;
      Check(ORS.rparen, "no )")
    END ;
    ptype.nofpar = nofpar; parblksize = size;
    if sym == ORS.colon:  (*function*)
      ORS.Get(sym);
      if sym == ORS.ident: qualident(obj);
        if (obj.class_ == ORB.Typ) and (obj.type_.form IN {ORB.Byte .. ORB.Pointer, ORB.Proc}): ptype.base = obj.type_
        else: ORS.Mark("illegal function type_")
        END
      else: ORS.Mark("type_ identifier expected")
      END
    END
  END
END ProcedureType;

def FormalType0(VAR typ: ORB.Type; dim: INTEGER);
  VAR obj: ORB.Object; dmy: LONGINT;
BEGIN
  if sym == ORS.ident:
    qualident(obj);
    if obj.class_ == ORB.Typ: typ = obj.type_ else: ORS.Mark("not a type_"); typ = ORB.intType END
  elif sym == ORS.array:
    ORS.Get(sym); Check(ORS.of, "OF ?");
    if dim >= 1: ORS.Mark("multi-dimensional open arrays not implemented") END ;
    NEW(typ); typ.form = ORB.Array; typ.len_ = -1; typ.size = 2*ORG.WordSize; 
    FormalType(typ.base, dim+1)
  elif sym == ORS.procedure:
    ORS.Get(sym); ORB.OpenScope;
    NEW(typ); typ.form = ORB.Proc; typ.size = ORG.WordSize; dmy = 0; ProcedureType(typ, dmy);
    typ.dsc = ORB.topScope.next; ORB.CloseScope
  else: ORS.Mark("identifier expected"); typ = ORB.noType
  END
END FormalType0;

def Type0(VAR type_: ORB.Type);
  VAR dmy: LONGINT; obj: ORB.Object; ptbase: PtrBase;
BEGIN type_ = ORB.intType; (*sync*)
  if (sym != ORS.ident) and (sym < ORS.array): ORS.Mark("not a type_");
    REPEAT ORS.Get(sym) UNTIL (sym == ORS.ident) or (sym >= ORS.array)
  END ;
  if sym == ORS.ident:
    qualident(obj);
    if obj.class_ == ORB.Typ:
      if (obj.type_ != None) and (obj.type_.form != ORB.NoTyp): type_ = obj.type_ END
    else: ORS.Mark("not a type_ or undefined")
    END
  elif sym == ORS.array: ORS.Get(sym); ArrayType(type_)
  elif sym == ORS.record:
    ORS.Get(sym); RecordType(type_); Check(ORS.end, "no END")
  elif sym == ORS.pointer:
    ORS.Get(sym); Check(ORS.to, "no TO");
    NEW(type_);  type_.form = ORB.Pointer; type_.size = ORG.WordSize; type_.base = ORB.intType;
    if sym == ORS.ident:
      obj = ORB.thisObj(); ORS.Get(sym);
      if obj != None:
        if (obj.class_ == ORB.Typ) and (obj.type_.form IN {ORB.Record, ORB.NoTyp}): type_.base = obj.type_
        else: ORS.Mark("no valid base type_")
        END
      END ;
      NEW(ptbase); ORS.CopyId(ptbase.name); ptbase.type_ = type_; ptbase.next = pbsList; pbsList = ptbase
    else: Type(type_.base);
      if type_.base.form != ORB.Record: ORS.Mark("must point to record") END
    END
  elif sym == ORS.procedure:
    ORS.Get(sym); ORB.OpenScope;
    NEW(type_); type_.form = ORB.Proc; type_.size = ORG.WordSize; dmy = 0;
    ProcedureType(type_, dmy); type_.dsc = ORB.topScope.next; ORB.CloseScope
  else: ORS.Mark("illegal type_")
  END
END Type0;

def Declarations(VAR varsize: LONGINT);
  VAR obj, first: ORB.Object;
    x: ORG.Item; tp: ORB.Type; ptbase: PtrBase;
    expo: BOOLEAN; id_: ORS.Ident;
BEGIN (*sync*) pbsList = None;
  if (sym < ORS.const) and (sym != ORS.end): ORS.Mark("declaration?");
    REPEAT ORS.Get(sym) UNTIL (sym >= ORS.const) or (sym == ORS.end)
  END ;
  if sym == ORS.const:
    ORS.Get(sym);
    while sym == ORS.ident:
      ORS.CopyId(id_); ORS.Get(sym); CheckExport(expo);
      if sym == ORS.eql: ORS.Get(sym) else: ORS.Mark("= ?") END;
      expression(x);
      if (x.type_.form == ORB.String) and (x.b == 2): ORG.StrToChar(x) END ;
      ORB.NewObj(obj, id_, ORB.Const); obj.expo = expo;
      if x.mode == ORB.Const: obj.val = x.a; obj.lev = x.b; obj.type_ = x.type_
      else: ORS.Mark("expression not constant"); obj.type_ = ORB.intType
      END;
      Check(ORS.semicolon, "; missing")
    END
  END ;
  if sym == ORS.type_:
    ORS.Get(sym);
    while sym == ORS.ident:
      ORS.CopyId(id_); ORS.Get(sym); CheckExport(expo);
      if sym == ORS.eql: ORS.Get(sym) else: ORS.Mark("=?") END ;
      Type(tp);
      ORB.NewObj(obj, id_, ORB.Typ); obj.type_ = tp; obj.expo = expo; obj.lev = level; tp.typobj = obj;
      if expo and (obj.type_.form == ORB.Record): obj.exno = exno; INC(exno) else: obj.exno = 0 END ;
      if tp.form == ORB.Record:
        ptbase = pbsList;  (*check whether this is base of a pointer type_; search and fixup*)
        while ptbase != None:
          if obj.name == ptbase.name:
            if ptbase.type_.base == ORB.intType: ptbase.type_.base = obj.type_ else: ORS.Mark("recursive record?") END
          END ;
          ptbase = ptbase.next
        END ;
        tp.len_ = dc;
        if level == 0: ORG.BuildTD(tp, dc) END    (*type_ descriptor; len_ used as its address*)
      END ;
      Check(ORS.semicolon, "; missing")
    END
  END ;
  if sym == ORS.var:
    ORS.Get(sym);
    while sym == ORS.ident:
      IdentList(ORB.Var, first); Type(tp);
      obj = first;
      while obj != None:
        obj.type_ = tp; obj.lev = level;
        if tp.size > 1: varsize = (varsize + 3) DIV 4 * 4 (*align*) END ;
        obj.val = varsize; varsize = varsize + obj.type_.size;
        if obj.expo: obj.exno = exno; INC(exno) END ;
        obj = obj.next
      END ;
      Check(ORS.semicolon, "; missing")
    END
  END ;
  varsize = (varsize + 3) DIV 4 * 4;
  ptbase = pbsList;
  while ptbase != None:
    if ptbase.type_.base.form == ORB.Int: ORS.Mark("undefined pointer base of") END ;
    ptbase = ptbase.next
  END ;
  if (sym >= ORS.const) and (sym <= ORS.var): ORS.Mark("declaration in bad order") END
END Declarations;

def ProcedureDecl;
  VAR proc: ORB.Object;
    type_: ORB.Type;
    procid: ORS.Ident;
    x: ORG.Item;
    locblksize, parblksize, L: LONGINT;
    int_: BOOLEAN;
BEGIN (* ProcedureDecl *) int_ = False; ORS.Get(sym);
  if sym == ORS.times: ORS.Get(sym); int_ = True END ;
  if sym == ORS.ident:
    ORS.CopyId(procid); ORS.Get(sym);
    (*Texts.WriteLn(W); Texts.WriteString(W, procid); Texts.WriteInt(W, ORG.Here(), 7);*)
    ORB.NewObj(proc, ORS.id_, ORB.Const); parblksize = 4;
    NEW(type_); type_.form = ORB.Proc; type_.size = ORG.WordSize; proc.type_ = type_;
    CheckExport(proc.expo);
    if proc.expo: proc.exno = exno; INC(exno) END ;
    ORB.OpenScope; INC(level); proc.val = -1; type_.base = ORB.noType;
    ProcedureType(type_, parblksize);  (*formal parameter list*)
    Check(ORS.semicolon, "no ;"); locblksize = parblksize; 
    Declarations(locblksize);
    proc.val = ORG.Here() * 4; proc.type_.dsc = ORB.topScope.next;
    if sym == ORS.procedure:
      L = 0; ORG.FJump(L);
      REPEAT ProcedureDecl; Check(ORS.semicolon, "no ;") UNTIL sym != ORS.procedure;
      ORG.FixLink(L); proc.val = ORG.Here() * 4; proc.type_.dsc = ORB.topScope.next
    END ;
    ORG.Enter(parblksize, locblksize, int_);
    if sym == ORS.begin: ORS.Get(sym); StatSequence END ;
    if sym == ORS.return:
      ORS.Get(sym); expression(x);
      if type_.base == ORB.noType: ORS.Mark("this is not a function")
      elif ~CompTypes(type_.base, x.type_, False): ORS.Mark("wrong result type_")
      END
    elif type_.base.form != ORB.NoTyp:
      ORS.Mark("function without result"); type_.base = ORB.noType
    END ;
    ORG.Return(type_.base.form, x, locblksize, int_);
    ORB.CloseScope; DEC(level); Check(ORS.end, "no END");
    if sym == ORS.ident:
      if ORS.id_ != procid: ORS.Mark("no match") END ;
      ORS.Get(sym)
    else: ORS.Mark("no proc id_")
    END
  END ;
  int_ = False
END ProcedureDecl;

def Module;
  VAR key: LONGINT;
    obj: ORB.Object;
    impid, impid1: ORS.Ident;
BEGIN Texts.WriteString(W, "  compiling "); ORS.Get(sym);
  if sym == ORS.module:
    ORS.Get(sym);
    if sym == ORS.times: version = 0; Texts.Write(W, "*"); ORS.Get(sym) else: version = 1 END ;
    ORB.Init; ORB.OpenScope;
    if sym == ORS.ident:
      ORS.CopyId(modid); ORS.Get(sym);
      Texts.WriteString(W, modid); Texts.Append(Oberon.Log, W.buf)
    else: ORS.Mark("identifier expected")
    END ;
    Check(ORS.semicolon, "no ;"); level = 0; dc = 0; exno = 1; key = 0;
    if sym == ORS.import:
      ORS.Get(sym);
      while sym == ORS.ident:
        ORS.CopyId(impid); ORS.Get(sym);
        if sym == ORS.becomes:
          ORS.Get(sym);
          if sym == ORS.ident: ORS.CopyId(impid1); ORS.Get(sym)
          else: ORS.Mark("id_ expected")
          END
        else: impid1 = impid
        END ;
        ORB.Import(impid, impid1);
        if sym == ORS.comma: ORS.Get(sym)
        elif sym == ORS.ident: ORS.Mark("comma missing")
        END
      END ;
      Check(ORS.semicolon, "no ;")
    END ;
    obj = ORB.topScope.next;
    ORG.Open(version); Declarations(dc); ORG.SetDataSize((dc + 3) DIV 4 * 4);
    while sym == ORS.procedure: ProcedureDecl; Check(ORS.semicolon, "no ;") END ;
    ORG.Header;
    if sym == ORS.begin: ORS.Get(sym); StatSequence END ;
    Check(ORS.end, "no END");
    if sym == ORS.ident:
      if ORS.id_ != modid: ORS.Mark("no match") END ;
      ORS.Get(sym)
    else: ORS.Mark("identifier missing")
    END ;
    if sym != ORS.period: ORS.Mark("period missing") END ;
    if ORS.errcnt == 0:
      ORB.Export(modid, newSF, key);
      if newSF: Texts.WriteLn(W); Texts.WriteString(W, "new symbol file ") END
    END ;
    if ORS.errcnt == 0:
      ORG.Close(modid, key, exno); Texts.WriteLn(W); Texts.WriteString(W, "compilation done ");
      Texts.WriteInt(W, ORG.pc, 6); Texts.WriteInt(W, dc, 6)
    else: Texts.WriteLn(W); Texts.WriteString(W, "compilation FAILED")
    END ;
    Texts.WriteLn(W); Texts.Append(Oberon.Log, W.buf);
    ORB.CloseScope; pbsList = None
  else: ORS.Mark("must start with MODULE")
  END
END Module;

def Option(VAR S: Texts.Scanner);
BEGIN newSF = False;
  if S.nextCh == "/":
    Texts.Scan(S); Texts.Scan(S);
    if (S.class_ == Texts.Name) and (S.s[0] == "s"): newSF = True END
  END
END Option;

def Compile*;
  VAR beg, end, time: LONGINT;
    T: Texts.Text;
    S: Texts.Scanner;
BEGIN Texts.OpenScanner(S, Oberon.Par.text, Oberon.Par.pos);
  Texts.Scan(S);
  if S.class_ == Texts.Char:
    if S.c == "@":
      Option(S); Oberon.GetSelection(T, beg, end, time);
      if time >= 0: ORS.Init(T, beg); Module END
    elif S.c == "^":
      Option(S); Oberon.GetSelection(T, beg, end, time);
      if time >= 0:
        Texts.OpenScanner(S, T, beg); Texts.Scan(S);
        if S.class_ == Texts.Name:
          Texts.WriteString(W, S.s); NEW(T); Texts.Open(T, S.s);
          if T.len_ > 0: ORS.Init(T, 0); Module END
        END
      END
    END
  else: 
    while S.class_ == Texts.Name:
      NEW(T); Texts.Open(T, S.s);
      if T.len_ > 0: Option(S); ORS.Init(T, 0); Module
      else: Texts.WriteString(W, S.s); Texts.WriteString(W, " not found");
        Texts.WriteLn(W); Texts.Append(Oberon.Log, W.buf)
      END ;
      if (T.len_ != 0) and (ORS.errcnt == 0): Texts.Scan(S) else: S.class_ = 0 END
    END
  END ;
  Oberon.Collect(0)
END Compile;

BEGIN Texts.OpenWriter(W); Texts.WriteString(W, "OR Compiler  5.11.2013");
  Texts.WriteLn(W); Texts.Append(Oberon.Log, W.buf);
  NEW(dummy); dummy.class_ = ORB.Var; dummy.type_ = ORB.intType;
  expression = expression0; Type = Type0; FormalType = FormalType0
END ORP.
