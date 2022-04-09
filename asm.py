from collections import defaultdict
import assembler as ASM


class LabelThunk(object):
  def __init__(self, name):
    self.name = name
  def __repr__(self):
    return '<LabelThunk %s>' % (self.name,)


class Context(dict):

  def __init__(self, symbol_table):
    self.symbol_table = symbol_table

  def __setitem__(self, item, value):
    if item in self.symbol_table:
      it = self.symbol_table[item]
      if isinstance(it, LabelThunk):
        print('assigning label %s -> %#06x' % (item, value))
        self.symbol_table[item] = value
      else:
        raise RuntimeError("Can't reassign labels %s" % (item,))
    dict.__setitem__(self, item, value)

  def __getitem__(self, item):
    try:
      return dict.__getitem__(self, item)
    except KeyError:
      print('New unassigned label:', item)
      thunk = self[item] = self.symbol_table[item] = LabelThunk(item)
      return thunk


def deco(bits_maker):  # Wrap a method that uses ASM.*() to make bits.

  def inner(method):

    def wrapper(self, a, b, K, v=0, u=0):

      if isinstance(K, LabelThunk):

        # For thunks build a function to do fix up.
        def fixup(value):
          # I'm so glad this reference to "wrapper" here works!
          wrapper(self, a, b, value, v, u)

        instruction = (fixup,)
        self.fixups[K].append(self.here)

      else:  # Otherwise just make the bits now.
        instruction = bits_maker(a, b, K, v=v, u=u)

      self.program[self.here] = instruction
      self.here += 4

    return wrapper

  return inner


def deco0(bits_maker):  # Wrap a method that uses ASM.*() to make bits.

  def inner(method):

    def wrapper(self, offset):

      if isinstance(offset, LabelThunk):

        def fixup(value):
          wrapper(self, value)
        instruction = (fixup,)
        self.fixups[offset].append(self.here)

      else:
        if offset % 4:
          raise RuntimeError('bad offset %r' % (offset,))
        offset = (offset - self.here) / 4 - 1
        instruction = bits_maker(offset)

      self.program[self.here] = instruction
      self.here += 4

    return wrapper

  return inner


class Assembler(object):

  def __init__(self):
    self.program = {}
    self.symbol_table = {}
    self.fixups = defaultdict(list)
    self.here = 0

    self.context = Context(self.symbol_table)

    for name in dir(Assembler):
      if not name.startswith('_'):
        value = getattr(self, name)
        if callable(value):
          self.context[name] = value

  def __call__(self, text):
    exec(text, self.context)
    del self.context['__builtins__']
    return self.program

  def label(self, thunk, reserves=0):
    if not isinstance(thunk, LabelThunk):
      raise RuntimeError('already assigned')
    name = self._name_of_label_thunk(thunk)
    self.context[name] = self.here
    self._fix(thunk, self.here)
    if reserves:
      assert reserves > 0, repr(reserves)
      self.here += reserves

  def _name_of_label_thunk(self, thunk):
    for name, value in self.symbol_table.items():
      if value is thunk:
        return name
    raise RuntimeError('No name for thunk %s' % (thunk,))

  def _fix(self, thunk, value):
    if thunk in self.fixups: # defaultdict!
      for addr in self.fixups.pop(thunk):
        fix = self.program[addr][0]
        print('fixing', thunk, 'at', hex(addr), 'to', hex(value), 'using', fix)
        temp, self.here = self.here, addr
        try:
          fix(value)
        finally:
          self.here = temp

#==-----------------------------------------------------------------------------
#  Move instructions

  def Mov(self, a, c, u=0):
    self.program[self.here] = ASM.Mov(a, c, u)
    self.here += 4

  def Mov_imm(self, a, K, v=0, u=0):
    self.program[self.here] = ASM.Mov_imm(a, K, v, u)
    self.here += 4

#==-----------------------------------------------------------------------------
#  RAM instructions

  def Load_byte(self, a, b, offset=0):
    self.program[self.here] = ASM.Load_byte(a, b, offset)
    self.here += 4

  def Load_word(self, a, b, offset=0):
    self.program[self.here] = ASM.Load_word(a, b, offset)
    self.here += 4

  def Store_byte(self, a, b, offset=0):
    self.program[self.here] = ASM.Store_byte(a, b, offset)
    self.here += 4

  def Store_word(self, a, b, offset=0):
    self.program[self.here] = ASM.Store_word(a, b, offset)
    self.here += 4

#==-----------------------------------------------------------------------------
#  Arithmetic/Logic instructions

  def Add(self, a, b, c, u=0):
    self.program[self.here] = ASM.Add(a, b, c, u)
    self.here += 4

  @deco(ASM.Add_imm)
  def Add_imm(self, a, b, K, v=0, u=0): pass

  def And(self, a, b, c, u=0):
    self.program[self.here] = ASM.And(a, b, c, u)
    self.here += 4

  @deco(ASM.And_imm)
  def And_imm(self, a, b, K, v=0, u=0): pass

  def Ann(self, a, b, c, u=0):
    self.program[self.here] = ASM.Ann(a, b, c, u)
    self.here += 4

  @deco(ASM.Ann_imm)
  def Ann_imm(self, a, b, K, v=0, u=0): pass

  def Asr(self, a, b, c, u=0):
    self.program[self.here] = ASM.Asr(a, b, c, u)
    self.here += 4

  @deco(ASM.Asr_imm)
  def Asr_imm(self, a, b, K, v=0, u=0): pass

  def Div(self, a, b, c, u=0):
    self.program[self.here] = ASM.Div(a, b, c, u)
    self.here += 4

  @deco(ASM.Div_imm)
  def Div_imm(self, a, b, K, v=0, u=0): pass

  def Ior(self, a, b, c, u=0):
    self.program[self.here] = ASM.Ior(a, b, c, u)
    self.here += 4

  @deco(ASM.Ior_imm)
  def Ior_imm(self, a, b, K, v=0, u=0): pass

  def Lsl(self, a, b, c, u=0):
    self.program[self.here] = ASM.Lsl(a, b, c, u)
    self.here += 4

  @deco(ASM.Lsl_imm)
  def Lsl_imm(self, a, b, K, v=0, u=0): pass

  def Mul(self, a, b, c, u=0):
    self.program[self.here] = ASM.Mul(a, b, c, u)
    self.here += 4

  @deco(ASM.Mul_imm)
  def Mul_imm(self, a, b, K, v=0, u=0): pass

  def Ror(self, a, b, c, u=0):
    self.program[self.here] = ASM.Ror(a, b, c, u)
    self.here += 4

  @deco(ASM.Ror_imm)
  def Ror_imm(self, a, b, K, v=0, u=0): pass

  def Sub(self, a, b, c, u=0):
    self.program[self.here] = ASM.Sub(a, b, c, u)
    self.here += 4

  @deco(ASM.Sub_imm)
  def Sub_imm(self, a, b, K, v=0, u=0): pass

  def Xor(self, a, b, c, u=0):
    self.program[self.here] = ASM.Xor(a, b, c, u)
    self.here += 4

  @deco(ASM.Xor_imm)
  def Xor_imm(self, a, b, K, v=0, u=0): pass

#==-----------------------------------------------------------------------------
#  Branch instructions

  def CC(self, c):
    self.program[self.here] = ASM.CC(c)
    self.here += 4

  @deco0(ASM.CC_imm)
  def CC_imm(self, offset): pass

  def CC_link(self, c):
    self.program[self.here] = ASM.CC_link(c)
    self.here += 4

  def CS(self, c):
    self.program[self.here] = ASM.CS(c)
    self.here += 4

  @deco0(ASM.CS_imm)
  def CS_imm(self, offset): pass

  def CS_link(self, c):
    self.program[self.here] = ASM.CS_link(c)
    self.here += 4

  def EQ(self, c):
    self.program[self.here] = ASM.EQ(c)
    self.here += 4

  @deco0(ASM.EQ_imm)
  def EQ_imm(self, offset): pass

  def EQ_link(self, c):
    self.program[self.here] = ASM.EQ_link(c)
    self.here += 4

  def F(self, c):
    self.program[self.here] = ASM.F(c)
    self.here += 4

  @deco0(ASM.F_imm)
  def F_imm(self, offset): pass

  def F_link(self, c):
    self.program[self.here] = ASM.F_link(c)
    self.here += 4

  def GE(self, c):
    self.program[self.here] = ASM.GE(c)
    self.here += 4

  @deco0(ASM.GE_imm)
  def GE_imm(self, offset): pass

  def GE_link(self, c):
    self.program[self.here] = ASM.GE_link(c)
    self.here += 4

  def GT(self, c):
    self.program[self.here] = ASM.GT(c)
    self.here += 4

  @deco0(ASM.GT_imm)
  def GT_imm(self, offset): pass

  def GT_link(self, c):
    self.program[self.here] = ASM.GT_link(c)
    self.here += 4

  def HI(self, c):
    self.program[self.here] = ASM.HI(c)
    self.here += 4

  @deco0(ASM.HI_imm)
  def HI_imm(self, offset): pass

  def HI_link(self, c):
    self.program[self.here] = ASM.HI_link(c)
    self.here += 4

  def LE(self, c):
    self.program[self.here] = ASM.LE(c)
    self.here += 4

  @deco0(ASM.LE_imm)
  def LE_imm(self, offset): pass

  def LE_link(self, c):
    self.program[self.here] = ASM.LE_link(c)
    self.here += 4

  def LS(self, c):
    self.program[self.here] = ASM.LS(c)
    self.here += 4

  @deco0(ASM.LS_imm)
  def LS_imm(self, offset): pass

  def LS_link(self, c):
    self.program[self.here] = ASM.LS_link(c)
    self.here += 4

  def LT(self, c):
    self.program[self.here] = ASM.LT(c)
    self.here += 4

  @deco0(ASM.LT_imm)
  def LT_imm(self, offset): pass

  def LT_link(self, c):
    self.program[self.here] = ASM.LT_link(c)
    self.here += 4

  def MI(self, c):
    self.program[self.here] = ASM.MI(c)
    self.here += 4

  @deco0(ASM.MI_imm)
  def MI_imm(self, offset): pass

  def MI_link(self, c):
    self.program[self.here] = ASM.MI_link(c)
    self.here += 4

  def NE(self, c):
    self.program[self.here] = ASM.NE(c)
    self.here += 4

  @deco0(ASM.NE_imm)
  def NE_imm(self, offset): pass

  def NE_link(self, c):
    self.program[self.here] = ASM.NE_link(c)
    self.here += 4

  def PL(self, c):
    self.program[self.here] = ASM.PL(c)
    self.here += 4

  @deco0(ASM.PL_imm)
  def PL_imm(self, offset): pass

  def PL_link(self, c):
    self.program[self.here] = ASM.PL_link(c)
    self.here += 4

  def T(self, c):
    self.program[self.here] = ASM.T(c)
    self.here += 4

  @deco0(ASM.T_imm)
  def T_imm(self, offset): pass

  def T_link(self, c):
    self.program[self.here] = ASM.T_link(c)
    self.here += 4

  def VC(self, c):
    self.program[self.here] = ASM.VC(c)
    self.here += 4

  @deco0(ASM.VC_imm)
  def VC_imm(self, offset): pass

  def VC_link(self, c):
    self.program[self.here] = ASM.VC_link(c)
    self.here += 4

  def VS(self, c):
    self.program[self.here] = ASM.VS(c)
    self.here += 4

  @deco0(ASM.VS_imm)
  def VS_imm(self, offset): pass

  def VS_link(self, c):
    self.program[self.here] = ASM.VS_link(c)
    self.here += 4


if __name__ == '__main__':
  from pprint import pformat

  asm = open('fillscreen.py').read()

  a = Assembler()
  p = a(asm)
  ##print pformat(p)
  #print 'a.here:', a.here

  program = []
  for addr in sorted(p):
    i = p[addr]
    program.append(i)
    try:
      e = ASM.dis(i)
    except:
      e = repr(i)
    print(hex(addr), e)
  #  print hex(addr), (p[addr])
