#MODULE  Modules;  (*NW 16.2.86 / 22.9.92*)

#	IMPORT SYSTEM, Kernel,
from collections import defaultdict
from util import word
import Files


MT = 12 # Module Table register.


class Kernel(object):
  ModList = None
  memory = defaultdict(int)

  @classmethod
  def AllocBlock(class_, size):
    return len(class_.memory)

  @classmethod
  def PUT(class_, p, val):
    assert p not in class_.memory
    class_.memory[p] = word(val)

SYSTEM = Kernel # Temporary, for convenience.

ModNameLen = 24; ObjMark = 0xF5; maximps = 32; headersize = 64;

class Module(object):
  def __init__(self,):
    self.Command = None
    self.ModuleName = []
    self.next = None
    self.size, self.IB, self.EB, self.RB, self.CB, self.PB, self.refcnt, self.key = (0 for _ in range(8))


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
##  (*search module in list; if not found, load module*)
##
##  VAR
##          mod, impmod, desc: Module;
##          ch: CHAR; k: SHORTINT;
##          i, j, offset, align, tdsize, tdadr: INTEGER;
##          nofimps, nofentries, nofptrs, comsize, constsize, codesize, nofrecs: INTEGER;
##          size, varsize, key, impkey, p, q, pb, eb: LONGINT;
##          init: Command;
##          F: Files.File; R: Files.Rider;
##          impname, modname: ModuleName;
##          import: ARRAY maximps OF Module;
##
##  PROCEDURE err(n: INTEGER);
##  BEGIN res := n; COPY(name, importing)
##  END err;

  res = 0
  mod = Kernel.ModList
  while mod is not None and mod.name != name:
    mod = mod.next
  if mod == None: # (*load*)
    R = OpenFile(name)
    if R:
##      Files.Set(R, F, 0)
      modname = Files.ReadString(R)
      key = Files.ReadInt(R)
      version = Files.ReadByte(R)
      size = Files.ReadInt(R)
      print 'Module', modname, key, version, size

      imports = {}
      impname = Files.ReadString(R)
      while impname:
        modnum = Files.ReadInt(R)
        imports[impname] = modnum
        impname = Files.ReadString(R)
      print 'Imports', imports

      tdx = Files.ReadInt(R) / 4
      type_descriptors = [
        Files.ReadInt(R)
        for _ in range(tdx)
        ]
      print 'type_descriptors', type_descriptors

      varsize = Files.ReadInt(R)
      print 'varsize', varsize

      strx = Files.ReadInt(R)
      strings = [
        Files.ReadString(R)
        for _ in range(tdx)
        ]
      print 'strings', strings

      code_length = Files.ReadInt(R)
      code = [
        Files.ReadCode(R) # Foul hackery!
        for _ in range(code_length)
        ]
      print 'code length', code_length

      commands = {}
      command_name = Files.ReadString(R)
      while command_name:
        num = Files.ReadInt(R)
        commands[command_name] = num
        command_name = Files.ReadString(R)
      print 'commands', commands

      nofent = Files.ReadInt(R)
      entry = Files.ReadInt(R)
      entries_and_pointers = []
      while entry != -1:
        entries_and_pointers.append(entry)
        entry = Files.ReadInt(R)
      print 'entries and pointer', entries_and_pointers

      fixorgP = Files.ReadInt(R)
      fixorgD = Files.ReadInt(R)
      fixorgT = Files.ReadInt(R)
      entry = Files.ReadInt(R)

      if Files.Read(R) != "O":
        raise ValueError

      print 'fixorgP', fixorgP
      print 'fixorgD', fixorgD
      print 'fixorgT', fixorgT
      print 'entry', entry

      mod = Module()
      mod.name = modname

      codesize = len(code)
      size = (headersize + nofent * 2 + len(imports)*4 + len(commands)*4
              + varsize + codesize*4)

      p = Kernel.AllocBlock(size)
      p += headersize

      mod.RB = p

      q = p + varsize
      while p < q:
        SYSTEM.PUT(p, 0)
        p += 1

      mod.PB = p

      q = p + codesize
      i = 0
      while p < q:
        SYSTEM.PUT(p, code[i])
        p += 1; i += 1

      fixD(Kernel.memory, mod, fixorgD)

  return mod


def fixD(mem, mod, fixorgD):
  adr = mod.PB + fixorgD
  while adr != mod.PB:
    i = mem[adr]
    mno = i[24:20]
    offs = i[20:]
    i[24:20] = MT
    i[20:] = mno # FIXME look up actual module addr in Module Table
    mem[adr] = i
    adr -= offs
  


'''
adr := mod.code + fixorgP*4;
WHILE adr # mod.code DO
  SYSTEM.GET(adr, inst);
  mno := inst DIV 100000H MOD 10H; (*decompose*)
  pno := inst DIV 1000H MOD 100H;
  disp := inst MOD 1000H;
  SYSTEM.GET(mod.imp + (mno-1)*4, impmod);
  SYSTEM.GET(impmod.ent + pno*4, dest); dest := dest + impmod.code;
  offset := (dest - adr - 4) DIV 4;
  SYSTEM.PUT(adr, (offset MOD 1000000H) + 0F7000000H); (*compose*)
  adr := adr - disp*4

'''


##
##      p := mod.IB; i := 0;
##      WHILE i < nofimps DO SYSTEM.PUT(p, import[i]); INC(p, 4); INC(i) END ;
##
##      (*entries*) q :=  nofentries*2 + p;
##      WHILE p < q DO Files.ReadBytes(R, i, 2); SYSTEM.PUT(p, i); INC(p, 2) END ;
##
##      (*pointer references*) q := nofptrs*2 + p;
##      WHILE p < q DO
##              Files.ReadBytes(R, i, 2); SYSTEM.PUT(p, i); INC(p, 2)
##      END ;
##
##      (*commands*) q := p + comsize;
##      WHILE p < q DO Files.Read(R, ch); SYSTEM.PUT(p, ch); INC(p) END ;
##      p := p + align;
##
##      (*constants*) q := p + constsize;
##      WHILE p < q DO Files.Read(R, ch); SYSTEM.PUT(p, ch); INC(p) END ;
##
##      (*variables*) q := p + varsize;
##      WHILE p < q DO SYSTEM.PUT(p, 0); INC(p) END ;
##
##      (*code*) q := p + codesize;
##      WHILE p < q DO Files.Read(R, ch); SYSTEM.PUT(p, ch); INC(p) END ;



##      IF ch # ObjMark THEN err(2); RETURN NIL END ;
##      Files.Read(R, ch); Files.ReadBytes(R, varsize, 4);  (*skip*)
##      Files.ReadBytes(R, nofimps, 2); Files.ReadBytes(R, nofentries, 2);
##      Files.ReadBytes(R, nofptrs, 2); Files.ReadBytes(R, comsize, 2);
##      Files.ReadBytes(R, constsize, 2); Files.ReadBytes(R, varsize, 4);
##      Files.ReadBytes(R, codesize, 2); Files.ReadBytes(R, nofrecs, 2);
##      Files.ReadBytes(R, key, 4); ReadName(R, modname);
##      align := (-((nofentries + nofptrs)*2 + comsize)) MOD 4;
##
##      (*imports*) res := 0; i := 0;
##      WHILE (i < nofimps) & (res = 0) DO
##              Files.ReadBytes(R, impkey, 4); ReadName(R, impname);
##              impmod := ThisMod(impname);
##              IF res = 0 THEN
##                      IF impmod.key = impkey THEN import[i] := impmod; INC(i); INC(impmod.refcnt)
##                      ELSE err(3); imported := impname
##                      END
##              END
##      END ;
##      IF res # 0 THEN (*undo*)
##              WHILE i > 0 DO DEC(i); DEC(import[i].refcnt) END ;
##              RETURN NIL
##      END ;
##
##      size := headersize + (nofentries +  nofptrs)*2 + nofimps*4 + comsize + 
##              varsize + codesize + constsize + align;
##      Kernel.AllocBlock(p, size); mod := SYSTEM.VAL(Module, p);
##      IF p = 0 THEN err(7); RETURN NIL END ;
##      mod.size := size;
##      mod.IB := p + headersize;
##      mod.EB := mod.IB + nofimps*4;
##      mod.RB := mod.EB + nofentries*2;
##      mod.CB := mod.RB + nofptrs*2;
##      mod.PB := mod.CB + comsize + align + constsize + varsize;
##      mod.refcnt := 0; mod.key := key;
##      COPY(modname, mod.name);
##
##      p := mod.IB; i := 0;
##      WHILE i < nofimps DO SYSTEM.PUT(p, import[i]); INC(p, 4); INC(i) END ;
##
##      (*entries*) q :=  nofentries*2 + p;
##      WHILE p < q DO Files.ReadBytes(R, i, 2); SYSTEM.PUT(p, i); INC(p, 2) END ;
##
##      (*pointer references*) q := nofptrs*2 + p;
##      WHILE p < q DO
##              Files.ReadBytes(R, i, 2); SYSTEM.PUT(p, i); INC(p, 2)
##      END ;
##
##      (*commands*) q := p + comsize;
##      WHILE p < q DO Files.Read(R, ch); SYSTEM.PUT(p, ch); INC(p) END ;
##      p := p + align;
##
##      (*constants*) q := p + constsize;
##      WHILE p < q DO Files.Read(R, ch); SYSTEM.PUT(p, ch); INC(p) END ;
##
##      (*variables*) q := p + varsize;
##      WHILE p < q DO SYSTEM.PUT(p, 0); INC(p) END ;
##
##      (*code*) q := p + codesize;
##      WHILE p < q DO Files.Read(R, ch); SYSTEM.PUT(p, ch); INC(p) END ;
##
##      (*link*) i := 0;
##      WHILE i < nofimps DO
##              pb := import[i].PB; eb := import[i].EB;
##              Files.ReadBytes(R, offset, 2); p := offset;
##              WHILE p # 0 DO  (*abs chain*)
##                      INC(p, mod.PB); SYSTEM.GET(p, q);
##                      SYSTEM.GET((q DIV 100H) MOD 100H * 2 + eb, offset);
##                      SYSTEM.PUT(p, disp(pb + offset)); p := q DIV 10000H
##              END ;
##              Files.ReadBytes(R, offset, 2); p := offset;
##              WHILE p # 0 DO  (*pc-rel chain*)
##                      INC(p, mod.PB); SYSTEM.GET(p, q);
##                      SYSTEM.GET((q DIV 100H) MOD 100H * 2 + eb, offset);
##                      SYSTEM.PUT(p, disp((pb + offset) - (p - 1))); p := q DIV 10000H
##              END ;
##              INC(i)
##      END ;
##
##      (*type descriptors*) i := 0;
##      WHILE i < nofrecs DO
##              Files.ReadBytes(R, tdsize, 2); Files.ReadBytes(R, tdadr, 2);
##              SYSTEM.NEW(desc, tdsize); SYSTEM.PUT(mod.PB + tdadr, desc);
##              p := SYSTEM.VAL(LONGINT, desc);
##              Files.ReadBytes(R, size, 4); SYSTEM.PUT(p, size); INC(p, 4);   (*header*)
##              Files.Read(R, k); j := 0;
##              WHILE j < k DO (*base tags*)
##                      Files.Read(R, ch); Files.ReadBytes(R, q, 4); (*offset or eno*)
##                      IF ch = 0X THEN INC(q, mod.PB)
##                      ELSE SYSTEM.GET(import[ORD(ch)-1].EB + q*2, offset);
##                              q := import[ORD(ch)-1].PB + offset
##                      END ;
##                      SYSTEM.GET(q, q); SYSTEM.PUT(p, q); INC(p, 4); INC(j)
##              END ;
##              WHILE j < 7 DO q := 0; SYSTEM.PUT(p, q); INC(p, 4); INC(j) END ;
##              Files.Read(R, k); j := 0;
##              WHILE j < k DO (*offsets*)
##                      Files.ReadBytes(R, offset, 2); SYSTEM.PUT(p, offset); INC(p, 2); INC(j)
##              END ;
##              INC(i)
##      END ;
##
##      init := SYSTEM.VAL(Command, mod.PB); init; res := 0
##
##
##                ELSE COPY(name, imported); err(1)
##                END
##        END ;
##        RETURN mod
##END ThisMod;
##
##PROCEDURE ThisCommand*(mod: Module; name: ARRAY OF CHAR): Command;
##        VAR i: INTEGER; ch: CHAR;
##                        comadr: LONGINT; com: Command;
##BEGIN com := NIL;
##        IF mod # NIL THEN
##                comadr := mod.CB; res := 5;
##                LOOP SYSTEM.GET(comadr, ch); INC(comadr);
##                        IF ch = 0X THEN (*not found*) EXIT END ;
##                        i := 0;
##                        LOOP
##                                IF ch # name[i] THEN EXIT END ;
##                                INC(i);
##                                IF ch = 0X THEN res := 0; EXIT END ;
##                                SYSTEM.GET(comadr, ch); INC(comadr)
##                        END ;
##                        IF res = 0 THEN (*match*)
##                                SYSTEM.GET(comadr, i); com := SYSTEM.VAL(Command, mod.PB + i); EXIT
##                        ELSE
##                                WHILE ch > 0X DO SYSTEM.GET(comadr, ch); INC(comadr) END ;
##                                INC(comadr, 2)
##                        END
##                END
##        END ;
##        RETURN com
##END ThisCommand;
##
##PROCEDURE unload(mod: Module; all: BOOLEAN);
##        VAR p: LONGINT; imp: Module;
##BEGIN p := mod.IB;
##        WHILE p < mod.EB DO  (*scan imports*)
##                SYSTEM.GET(p, imp);
##                IF imp # NIL THEN
##                        DEC(imp.refcnt);
##                        IF all & (imp.refcnt = 0) THEN unload(imp, all) END
##                END ; 
##                INC(p, 4)
##        END ;
##        Kernel.FreeBlock(SYSTEM.VAL(LONGINT, mod))
##END unload;
##
##PROCEDURE Free*(name: ARRAY OF CHAR; all: BOOLEAN);
##        VAR mod: Module;
##BEGIN mod :=  SYSTEM.VAL(Module, Kernel.ModList);
##        LOOP
##                IF mod = NIL THEN res := 1; EXIT END ;
##                IF name = mod.name THEN
##                        IF mod.refcnt = 0 THEN unload(mod, all); res := 0 ELSE res := 2 END ;
##                        EXIT
##                END ;
##                mod := mod.next
##        END
##END Free;
##
##BEGIN
##IF Kernel.err = 0 THEN loop := ThisCommand(ThisMod("Oberon"), "Loop") END ;
##loop
##END Modules.


if __name__ == '__main__':
  from disassembler import dis
  from risc import RISC

  # Load the module binary.
  m = ThisMod('Pattern1')

  # Display the RAM contents after loading.
  print
  for address in sorted(Kernel.memory):
    instruction = Kernel.memory[address]
    b = bin(instruction)[2:]
    b = '0' * (32 - len(b)) + b
    print 'memory[0x%04x] = 0x%08x %s %s' % (address, instruction, b, dis(instruction))
  print
  print

  # "Initialize" the module's variable data so we can see it.
  for n in range(16):
    Kernel.memory[n] = n + 1

  risc_cpu = RISC(Kernel.memory, m.PB)

  Kernel.memory[risc_cpu.R[MT]] = m.RB # Set up the Module Table (sort of).

##  risc_cpu.R[13] = 0x0044 # Set Static Base pointer SB.
  risc_cpu.R[14] = 0x0040 # Set Stack pointer SP.
  while risc_cpu.pcnext:
    risc_cpu.cycle()
    risc_cpu.view()
