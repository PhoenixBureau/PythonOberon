#!/usr/bin/env python
#MODULE  Modules;  (*NW 16.2.86 / 22.9.92*)

#	IMPORT SYSTEM, Kernel,
from ram import ByteAddressed32BitRAM
from util import word
import Files


MT = 12 # Module Table register.
SB = 14 # Stack
DescSize = 80


root = None # Global module list.
MTOrg = 0x100 # Why not?
AllocPtr = 0


class Kernel(object):
  memory = ByteAddressed32BitRAM()
  ModuleTable=0x10
  mt_offset=0x0

  @classmethod
  def AllocBlock(class_, size):
    return len(class_.memory)

  @classmethod
  def PUT(class_, p, val):
    assert p == (p / 4 * 4), repr(p)
    class_.memory[p] = val

  @classmethod
  def PUTBYTE(class_, p, val):
    class_.memory.put_byte(p, val)

  @classmethod
  def GET(class_, p):
    assert p == (p / 4 * 4), repr(p)
    return class_.memory[p]

  @classmethod
  def entable_module(class_, mod):
    mt_entry = class_.ModuleTable + class_.mt_offset
    class_.memory[mt_entry] = mod.data
    mod.num = class_.mt_offset / 4
    class_.mt_offset +=4
##    print 'setting module %s to num %i' % (mod.name, mod.num)


SYSTEM = Kernel # Temporary, for convenience.

ModNameLen = 24; ObjMark = 0xF5; maximps = 32; headersize = 64;

class Module(object):
  def __init__(self, name):
    self.name = name
    self.next = None
    (self.size, self.num, self.refcnt, self.key,
     self.data, self.code, self.imp, self.ent, self.ptr
     )= (0 for _ in range(9))


##VAR res*: INTEGER;
##        importing*, imported*: ModuleName;
##        loop: Command;
##
##(*Exported procedures: ThisMod, Free, ThisProc*)

def ReadName(R):
  return Files.ReadString(R)

def OpenFile(name):
  name += '.rsc'
  return Files.Old(name)

##PROCEDURE disp(a: LONGINT): LONGINT;
##        VAR d: LONGINT; i: INTEGER;
##BEGIN d := 0; a := a MOD 40000000H + 0C0000000H; i := 0;
##        REPEAT d := SYSTEM.LSH(d, 8) + (a MOD 100H); a := SYSTEM.LSH(a, -8); INC(i)
##        UNTIL i = 4;
##        RETURN d
##END disp;

def ThisMod(name):
  global root, AllocPtr
  res = 0
  nofimps = 0
  import_ = [None] * 16
  mod = root
  while mod is not None and mod.name != name:
    mod = mod.next
  if mod == None: # (*load*)
    print 'loading:', name
    R = OpenFile(name)
    if R:
##      Files.Set(R, F, 0)
      modname = Files.ReadString(R)
      key = Files.ReadInt(R)
      version = Files.ReadByte(R)
      size = Files.ReadInt(R)
      print 'Module', modname, key, version, size

      impname = Files.ReadString(R)
      while impname:
        impkey = Files.ReadInt(R)
        impmod = ThisMod(impname)
        import_[nofimps] = impmod
        impmod.refcnt += 1
        nofimps += 1
        impname = Files.ReadString(R)
      print 'Imports', import_

      mod = Module(modname)
      mod.data = p = AllocPtr
      AllocPtr = (p + size + 0x10) / 0x20 * 0x20
      mod.size = AllocPtr - p
      mod.num = 1 if root is None else (root.num + 1)
      mod.next = root
      root = mod

      p += DescSize
      mod.key = key
      SYSTEM.PUT(mod.num * 4 + MTOrg, p) # (*module table entry*)

      n = Files.ReadInt(R)
      print 'type_descriptors', n
      for _ in range(0, n, 4):
        w = Files.ReadInt(R)
        SYSTEM.PUT(p, w)
        p += 4

      varsize = Files.ReadInt(R)
      assert varsize == (varsize / 4 * 4), repr(varsize)
      print 'varsize', varsize
      q = p + varsize
      while p < q:
        SYSTEM.PUT(p, 0)
        p += 4

      strx = Files.ReadInt(R)
      print 'strings', strx
      for _ in range(strx):
        ch = Files.Read(R)
        SYSTEM.PUTBYTE(p, ch)
        p += 1
      while p % 4:
        SYSTEM.PUTBYTE(p, 0)
        p += 1

      mod.code = p

      code_length = Files.ReadInt(R)
      print 'code length', code_length
      for _ in range(0, code_length, 4):
        instruction = Files.ReadCode(R) # Foul hackery!
        SYSTEM.PUT(p, instruction)
        p += 4

      mod.imp = p # (*copy imports*)

      for i, impmod in enumerate(import_):
        if impmod is not None:
          SYSTEM.PUT(p, impmod.data)
          p += 4

      mod.cmd = p # (*commands*)
      ch = Files.Read(R)
      while ch:
        while ch:
          SYSTEM.PUTBYTE(p, ch)
          p += 1
          ch = Files.Read(R)
        while p % 4:
          SYSTEM.PUTBYTE(p, 0)
          p += 1
        n = Files.ReadInt(R)
        SYSTEM.PUT(p, n)
        p += 4
        ch = Files.Read(R)
      while p % 4:
        SYSTEM.PUTBYTE(p, 0)
        p += 1

      mod.ent = p # (*entries*)

      nofent = Files.ReadInt(R)
      for _ in range(nofent):
        w = Files.ReadInt(R)
        SYSTEM.PUT(p, w)
        p += 4

      mod.ptr = p # (*pointer references*)

      w = Files.ReadInt(R)
      while w >= 0:
        SYSTEM.PUT(p, mod.data + w)
        p += 4
        w = Files.ReadInt(R)
      SYSTEM.PUT(p, 0)
      p += 4

      fixorgP = Files.ReadInt(R)
      fixorgD = Files.ReadInt(R)
      fixorgT = Files.ReadInt(R)

      w = Files.ReadInt(R)
      body = mod.code + w

      if Files.Read(R) != "O":
        raise ValueError

      print 'fixorgP', fixorgP
      print 'fixorgD', fixorgD
      print 'fixorgT', fixorgT
      print

      # (*fixup of BL*)
      adr = mod.code + fixorgP * 4
      while adr != mod.code:
        inst = SYSTEM.GET(adr)
        mno = inst / 0x100000 % 0x10
        pno = inst / 0x1000 % 0x100
        disp = inst % 0x1000
        impmod_data_addr = SYSTEM.GET(mod.imp + (mno - 1) * 4)
        impmod = look_up_module_by_data_addr(impmod_data_addr)
        dest = SYSTEM.GET(impmod.ent + pno * 4)
        dest = dest + impmod.code
        offset = (dest - adr - 4) / 4
        SYSTEM.PUT(adr, (offset % 0x1000000) + 0x0F7000000)
        adr = adr - disp * 4

      # (*fixup of LDR/STR/ADD*)
      adr = mod.code + fixorgD * 4
      while adr != mod.code:
        inst = SYSTEM.GET(adr)
        mno = inst / 0x100000 % 0x10
        disp = inst % 0x1000
        if not mno: # (*global*)
          SYSTEM.PUT(adr, (inst / 0x1000000 * 0x10 + MT) * 0x100000 + mod.num * 4)

        else: # (*import*)
          impmod_data_addr = SYSTEM.GET(mod.imp + (mno - 1) * 4)
          impmod = look_up_module_by_data_addr(impmod_data_addr)
          v = impmod.num
          SYSTEM.PUT(adr, (inst / 0x1000000 * 0x10 + MT) * 0x100000 + v*4)

          inst = SYSTEM.GET(adr + 4)
          vno = inst % 0x100
          offset = SYSTEM.GET(impmod.ent + vno * 4)
          if (inst / 0x100) % 2:
            offset = offset + impmod.code - impmod.data
          SYSTEM.PUT(adr+4, inst / 0x10000 * 0x10000 + offset)

        adr = adr - disp * 4

      # (*fixup of type descriptors*)
      adr = mod.data + fixorgT * 4
      while adr != mod.data:
        inst = SYSTEM.GET(adr)
        mno = inst / 0x1000000 % 0x10
        vno = inst / 0x1000 % 0x1000
        disp = inst % 0x1000
        if not mno: # (*global*)
          inst = mod.data + vno
        else: # (*import*)
          impmod_data_addr = SYSTEM.GET(mod.imp + (mno - 1) * 4)
          impmod = look_up_module_by_data_addr(impmod_data_addr)
          offset = SYSTEM.GET(impmod.ent + vno * 4)
          inst = impmod.data + offset

        SYSTEM.PUT(adr, inst)
        adr = adr - disp * 4

  return mod


def look_up_module_by_data_addr(impmod_data_addr):
  global root
  mod = root
  while mod is not None and mod.data != impmod_data_addr:
    mod = mod.next
  return mod

      
##def fixD(mem, mod, fixorgD, imported_modules):
##  adr = mod.code + fixorgD * 4
##  while adr != mod.code:
##    i = mem[adr]
##    mno = i[24:20]
##    if not mno:
##      m = mod
##    else:
##      m = imported_modules[mno - 1]
##    offset = m.num * 4
##    offs = i[20:]
##    i[24:20] = MT
##    i[20:] = offset
##    mem[adr] = i
##    adr -= offs * 4
  

if __name__ == '__main__':
  import sys
  from disassembler import dis
  from devices import BlockDeviceWithDMI
  from risc import RISC

  if len(sys.argv) > 1:
    modname = sys.argv[-1].partition('.')[0]
  else:
    modname = 'Pattern1'

  # Load the module binary.
  m = ThisMod(modname)

##  # Display the RAM contents after loading.
##  print
##  for address in range(m.code, len(Kernel.memory)+1, 4):
##    instruction = Kernel.memory[address]
##    b = bin(instruction)[2:]
##    b = '0' * (32 - len(b)) + b
##    print 'memory[0x%04x] = 0x%08x %s %s' % (address, instruction, b, dis(instruction))
##  print
##  print
##
##  if '-r' in sys.argv:
##    risc_cpu = RISC(Kernel.memory, m.code)
##    risc_cpu.R[MT] = Kernel.ModuleTable
##    risc_cpu.R[SB] = 0x1000 # Set Stack pointer SP.
##
##    store = risc_cpu.io_ports[32] = BlockDeviceWithDMI(Kernel.memory)
##
##    while risc_cpu.pcnext:
##      risc_cpu.cycle()
##      risc_cpu.view()
