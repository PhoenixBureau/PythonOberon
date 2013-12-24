'''
MODULE ORB;   (*NW 7.10.2013   in Oberon-07*)
  IMPORT Files, ORS;
  (*Definition of data types Object and Type, which together form the data structure
    called "symbol table". Contains procedures for creation of Objects, and for search:
    NewObj, this, thisimport, thisfield (and OpenScope, CloseScope).
    Handling of import and export, i.e. reading and writing of "symbol files" is done by procedures
    Import and Export. This module contains the list of standard identifiers, with which
    the symbol table (universe), and that of the pseudo-module SYSTEM are initialized. *)

'''
import ORSX, Files

versionkey = 1; maxTypTab = 64;
Head = 0;
Const = 1; Var = 2; Par = 3; Fld = 4; Typ = 5;
SProc = 6; SFunc = 7; Mod = 8;

Byte = 1; Bool = 2; Char = 3; Int = 4; Real = 5; Set = 6;
Pointer = 7; NilTyp = 8; NoTyp = 9; Proc = 10;
String = 11; Array = 12; Record = 13;


class Object:
  def __init__(self,):
    self.class_, self.lev, self.exno = 0,0,0
    self.expo, self.rdo = False, False #   (*exported / read-only*)
    self.next, self.dsc = None, None
    self.type_ = None
    self.name = None
    self.val = 0


class Module(Object):
  def __init__(self,):
    Object.__init__(self)
    self.orgname = None


class Type:
  def __init__(self,):
    self.form, self.ref, self.mno = 0,0,0
    self.nofpar = 0
    self.len_ = 0
    self.dsc = self.typobj = None
    self.base = None
    self.size = 0

topScope = None
universe, system = None,None
byteType, boolType, charType = None,None,None
intType, realType, setType, nilType, noType, strType = None,None,None,None,None,None
nofmod, Ref = 0,0
typtab = {}


def NewObj(obj, id_, class_):
  '''(*insert new Object with name id*)'''

  x = topScope
  while (x.next != None) and (x.next.name != id_):
    x = x.next

  if x.next == None:
    new = Object()
    new.name = id_
    new.class_ = class_
    obj = x.next = new
  else:
    obj = x.next
    ORSX.Mark("mult def")

  return obj


def _e(l):
  return ''.join(char for char in l if char and isinstance(char, basestring))

def thisObj():
  s = topScope
  while True:
    x = s.next
    while (x != None) and (x.name != _e(ORSX.id_)):
      x = x.next
    s = s.dsc
    if (x != None) or (s is None):
      break
  return x


def thisimport(mod):
  if mod.rdo:
    if mod.name[0] != 0x0:
      obj = mod.dsc
      while (obj != None) and (obj.name != _e(ORSX.id_)):
        obj = obj.next
    else:
      obj = None
  else:
    obj = None
  return obj


def thisfield(rec):
  fld = rec.dsc
  while (fld != None) and (fld.name != _e(ORSX.id_)):
    fld = fld.next
  return fld


def OpenScope():
  global topScope
  s = Object()
  s.class_ = Head
  s.dsc = topScope
  topScope = s


def CloseScope():
  global topScope
  topScope = topScope.dsc


#  (*------------------------------- Import ---------------------------------*)

def MakeFileName(name, ext):
  return name + ext


def ThisModule(name, orgname, non, key):
  global nofmod

  obj1 = topScope
  obj = obj1.next #  (*search for module*)
  while (obj != None) and (obj.name != name):
    obj1 = obj
    obj = obj1.next

  if obj == None: # (*insert new module*)
    mod = Module()
    mod.class_ = Mod
    mod.name = name
    mod.orgname = orgname
    mod.val = key
    mod.lev = nofmod
    nofmod += 1
    mod.type = noType
    obj1.next = mod
    obj = mod
  else: # (*module already present*)
    if non:
      ORSX.Mark("invalid import order")
  return obj



def Read(R):
  b = Files.ReadByte(R)
  if b < 0x80:
    x = b
  else:
    x = b - 0x100
  return x
 
def InType(R, thismod):
  ref = Read(R)
  if ref < 0:
    T = typtab[-ref] # (*already read*)
  else:
    t = Type()
    T = t
    typtab[ref] = t
    t.mno = thismod.lev
    form = Read(R)
    t.form = form

    if form == Pointer:
      t.base = InType(R, thismod)
      t.size = 4

    elif form == Array:
      t.base = InType(R, thismod)
      t.len = Files.ReadNum(R, )
      t.size = Files.ReadNum(R, )

    elif form == Record:
      t.base = InType(R, thismod)
      if t.base.form == NoTyp:
        t.base = None;
        obj = None
      else:
        obj = t.base.dsc
      t.len = Files.ReadNum(R) # (*TD adr/exno*)
      t.nofpar = Files.ReadNum(R) #  (*ext level*)
      t.size = Files.ReadNum(R)
      Read(R, class_);
      while class_ != 0: # (*fields*)
        fld = Object()
        fld.class_ = class_
        fld.name = Files.ReadString(R);
        if fld.name[0] != 0x0:
          fld.expo = True
          fld.type = InType(R, thismod)
        else:
          fld.expo = False
          fld.type = nilType
        fld.val = Files.ReadNum(R)
        fld.next = obj
        obj = fld
        class_ = Read(R)
      t.dsc = obj

    elif form == Proc:
      t.base = InType(R, thismod)
      obj = None
      np = 0
      class_ = Read(R)
      while class_ != 0: # (*parameters*)
        NEW(par)
        par.class_ = class_
        readonly = Read(R)
        par.rdo = readonly == 1 
        par.type = InType(R, thismod)
        par.next = obj
        obj = par
        np += 1
        class_ = Read(R)
      t.dsc = obj
      t.nofpar = np
      t.size = 4

    modname = Files.ReadString(R)

    if modname[0] != 0x0: # (*re-import*)
      key = Files.ReadInt(R)
      name = Files.ReadString(R)
      mod = ThisModule(modname, modname, False, key);
      obj = mod.dsc # (*search type*)
      while (obj != None) and (obj.name != name):
        obj = obj.next
      if obj != None:
        T = obj.type # (*type object found in object list of mod*)
      else:           # (*insert new type object in object list of mod*)
        obj = Object()
        obj.name = name
        obj.class_ = Typ
        obj.next = mod.dsc
        mod.dsc = obj
        obj.type = t
        t.mno = mod.lev
        T = t

      typtab[ref] = T
  return T


def Import(modid, modid1):
  global nofmod
  if modid1 == "SYSTEM":
    thismod = ThisModule(modid, modid1, True, key)
    nofmod -= 1
    thismod.lev = 0
    thismod.dsc = system
    thismod.rdo = True
  else:
    fname = MakeFileName(modid1, ".smb")
    R = Files.Old(fname)
    if R != None:
#      Files.Set(R, F, 0)
      Files.ReadInt(R) # discard.
      key = Files.ReadInt(R)
      modname = Files.ReadString(R);
      thismod = ThisModule(modid, modid1, True, key)
      thismod.rdo = True;

      class_ = Read(R) # (*version key*)
      if class_ != versionkey:
        ORSX.Mark("wrong version")

      class_ = Read(R)
      while class_ != 0:
        obj = Object()
        obj.class_ = class_
        obj.name = Files.ReadString(R)
        obj.typ = eInType(R, thismod)
        obj.lev = -thismod.lev;
        if class_ == Typ:
          t = obj.type
          t.typobj = obj
          k = Read(R) # (*fixup bases of previously declared pointer types*)
          while k != 0:
            typtab[k].base = t
            k = Read(R)
        else:
          if class_ == Const:
            if obj.type.form == Real:
              obj.val = Files.ReadInt(R)
            else:
              obj.val = Files.ReadNum(R)
          elif class_ == Var:
            obj.val = Files.ReadNum(R)
            obj.rdo = True
        obj.next = thismod.dsc
        thismod.dsc = obj
        class_ = Read(R)

    else:
      ORS.Mark("import not available")


#  (*-------------------------------- Export ---------------------------------*)

def Write(R, x):
  Files.WriteByte(R, x) # (* -128 <= x < 128 *)


def OutType(R, t):

  def OutPar(R, par, n):
    if n > 0:
      OutPar(R, par.next, n-1)
      cl = par.class_
      Write(R, cl)
      if par.rdo:
        Write(R, 1)
      else:
        Write(R, 0)
      OutType(R, par.type)

  def FindHiddenPointers(R, typ, offset):
    if (typ.form == Pointer) or (typ.form == NilTyp):
      Write(R, Fld)
      Write(R, 0)
      Files.WriteNum(R, offset)
    elif typ.form == Record:
      fld = typ.dsc
      while fld != None:
        FindHiddenPointers(R, fld.type, fld.val + offset)
        fld = fld.next
    elif typ.form == Array:
      i = 0
      n = typ.len
      while i < n:
        FindHiddenPointers(R, typ.base, typ.base.size * i + offset)
        i += 1

  if t.ref > 0: # (*type was already output*)
    Write(R, -t.ref)
  else:
    obj = t.typobj
    if obj != None:
      Write(R, Ref)
      t.ref = Ref
      Ref += 1
    else: # (*anonymous*)
      Write(R, 0)

    Write(R, t.form);
    if t.form == Pointer:
      if t.base.ref > 0:
        Write(R, -t.base.ref)
      elif (t.base.typobj == None) or not t.base.typobj.expo: # (*base not exported*)
        Write(R, -1)
      else:
        OutType(R, t.base)

    elif t.form == Array:
      OutType(R, t.base)
      Files.WriteNum(R, t.len)
      Files.WriteNum(R, t.size)

    elif t.form == Record:
      if t.base != None:
        OutType(R, t.base)
      else:
        OutType(R, noType)

      if obj != None:
        Files.WriteNum(R, obj.exno)
      else:
        Write(R, 0)
      Files.WriteNum(R, t.nofpar)
      Files.WriteNum(R, t.size)
      fld = t.dsc
      while fld != None: # (*fields*)
        if fld.expo:
          Write(R, Fld)
          Files.WriteString(R, fld.name)
          OutType(R, fld.type)
          Files.WriteNum(R, fld.val)
        else:
          FindHiddenPointers(R, fld.type, fld.val)

        fld = fld.next

      Write(R, 0) # indentation!?

    elif t.form == Proc:
      OutType(R, t.base)
      OutPar(R, t.dsc, t.nofpar)
      Write(R, 0)

    if (t.mno > 0) and (obj != None): # (*re-export, output name*)
      mod = topScope.next
      while (mod != None) and (mod.lev != t.mno):
        mod = mod.next
      if mod != None:
        Files.WriteString(R, mod.name)
        Files.WriteInt(R, mod.val)
        Files.WriteString(R, obj.name)
      else :
        ORS.Mark("re-export not found")
        Write(R, 0)
    else:
      Write(R, 0)

def Export(modid, newSF, key):

  Ref = Record + 1
  filename = MakeFileName(modid, ".smb")
  R = Files.New(filename)
#  Files.Set(R, F, 0)
  Files.WriteInt(R, 0) #(*placeholder*)
  Files.WriteInt(R, 0) #(*placeholder for key to be inserted at the end*)
  Files.WriteString(R, modid)
  Write(R, versionkey)

  obj = topScope.next
  while obj != None:
    if obj.expo:
      Write(R, obj.class_)
      Files.WriteString(R, obj.name)
      OutType(R, obj.type)
      if obj.class_ == Typ:
        if obj.type.form == Record:
          obj0 = topScope.next # (*check whether this is base of previously declared pointer types*)
          while obj0 != obj:
            if (obj0.type.form == Pointer) and (obj0.type.base == obj.type) and (obj0.type.ref > 0):
              Write(R, obj0.type.ref)
            obj0 = obj0.next

        Write(R, 0)

      elif obj.class_ == Const:
        if obj.type.form == Proc:
          Files.WriteNum(R, obj.exno)
        elif obj.type.form == Real:
          Files.WriteInt(R, obj.val)
        else:
          Files.WriteNum(R, obj.val)

      elif obj.class_ == Var:
        Files.WriteNum(R, obj.exno)
        if obj.type.form == String:
          Files.WriteNum(R, obj.val / 0x10000)
          obj.val = obj.val % 0x10000

    obj = obj.next

##  while True:
##    Write(R, 0)
##    if Files.Length(F) % 4 == 0:
##      break

  for Ref in range(Record+1, maxTypTab): # Double check range! FIXME
    typtab[Ref] = None

##  Files.Set(R, F, 0)
##  sum = 0; # (* compute key (checksum) *)
##  while not R.eof:
##    Files.ReadInt(R, x)
##    sum = sum + x
##
##  F1 = Files.Old(filename)  # (*sum is new key*)
##  if F1 != None:
##    Files.Set(R1, F1, 4)
##    Files.ReadInt(R1, oldkey)
##  else:
##    oldkey = sum+1
##
##  if sum != oldkey:
##    if newSF:
##      key = sum
##      Files.Set(R, F, 4)
##      Files.WriteInt(R, sum)
##      Files.Register(F) # (*insert checksum*)
##    else:
##      ORS.Mark("new symbol file inhibited")
##
##  else:
##    newSF = False
##    key = sum

  return modid, newSF, key


def Init():
  global topScope, nofmod
  topScope = universe
  nofmod = 1

  
def type_(ref, form, size):
  tp = Type()
  tp.form = form
  tp.size = size
  tp.ref = ref
  tp.base = None
  typtab[ref] = tp
  return tp

byteType = type_(Byte, Int, 1);
boolType = type_(Bool, Bool, 1);
charType = type_(Char, Char,1);
intType = type_(Int, Int, 4);
realType = type_(Real, Real, 4);
setType = type_(Set, Set,4);
nilType = type_(NilTyp, NilTyp, 4);
noType = type_(NoTyp, NoTyp, 4);
strType = type_(String, String, 8);

def enter(name, cl, ty, n):
  global system
  obj = Object()
  obj.name = name
  obj.class_ = cl
  obj.type_ = ty
  obj.val = n
  obj.dsc = None
  if cl == Typ:
    ty.typobj = obj
  obj.next = system
  system = obj

 
##  (*initialize universe with data types and in-line procedures;
##    LONGINT is synonym to INTEGER, LONGREAL to REAL.
##    LED, ADC, SBC; LDPSR, LDREG, REG, COND, MSK are not in language definition*)

system = None #  (*n == procno*10 + nofpar*)
enter("UML", SFunc, intType, 132); # (*functions*)
enter("SBC", SFunc, intType, 122);
enter("ADC", SFunc, intType, 112);
enter("ROR", SFunc, intType, 92);
enter("ASR", SFunc, intType, 82);
enter("LSL", SFunc, intType, 72);
enter("LEN", SFunc, intType, 61);
enter("CHR", SFunc, charType, 51);
enter("ORD", SFunc, intType, 41);
enter("FLT", SFunc, realType, 31);
enter("FLOOR", SFunc, intType, 21);
enter("ODD", SFunc, boolType, 11);
enter("ABS", SFunc, intType, 1);
enter("LED", SProc, noType, 81); # (*procedures*)
enter("UNPK", SProc, noType, 72);
enter("PACK", SProc, noType, 62);
enter("NEW", SProc, noType, 51);
enter("ASSERT", SProc, noType, 41);
enter("EXCL", SProc, noType, 32);
enter("INCL", SProc, noType, 22);
enter("DEC", SProc, noType, 11);
enter("INC", SProc, noType, 1);
enter("SET", Typ, setType, 0);  # (*types*)
enter("BOOLEAN", Typ, boolType, 0);
enter("BYTE", Typ, byteType, 0);
enter("CHAR", Typ, charType, 0);
enter("LONGREAL", Typ, realType, 0);
enter("REAL", Typ, realType, 0);
enter("LONGINT", Typ, intType, 0);
enter("INTEGER", Typ, intType, 0);

topScope = None;
OpenScope()
topScope.next = system
universe = topScope

system = None; # (* initialize "unsafe" pseudo-module SYSTEM*)
enter("H", SFunc, intType, 201); #    (*functions*)
enter("COND", SFunc, boolType, 191);
enter("SIZE", SFunc, intType, 181);
enter("ADR", SFunc, intType, 171);
enter("VAL", SFunc, intType, 162);
enter("REG", SFunc, intType, 151);
enter("BIT", SFunc, boolType, 142);
enter("LDREG", SProc, noType, 142); # (*procedures*)
enter("LDPSR", SProc, noType, 131);
enter("COPY", SProc, noType, 123);
enter("PUT", SProc, noType, 112);
enter("GET", SProc, noType, 102);
