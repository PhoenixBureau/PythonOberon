import pdb
from sys import stderr
from pprint import pformat
from util import bint, blong, py2signed, signed2py
from assembler import dis


F = 2**32-1
IO_RANGE = 0x0FFFFFFC0
ROMStart = 0xFFFFF800 / 4
MemSize = 0x00180000
MemWords = MemSize / 4

#define DisplayStart 0x000E7F00


class Trap(Exception):
  pass


class RISC(object):

  MT = 12 # Module Table register.

  def __init__(self, rom, ram, PC=ROMStart):
    self.rom = rom
    self.ram = ram
    self.PC = self.pcnext = PC
    self.R = [0] * 16
    self.H = 0
    self.N = self.Z = self.C = self.OV = 0
    self.io_ports = {}

  def cycle(self):
    self.PC = self.pcnext
    instruction = self.fetch()
##    if self.PC < MemWords:
##      print '0x%08x : 0x%08x %i %i %i %i %i %i %i %i %i %i %i %i %i %i %i 0x%x' % ((self.PC, instruction,
##                                                                                 ) + tuple(map(signed2py, self.R[:-1]))
##                                                                                 + (self.R[-1],))
    self.decode(instruction)
    self.what_are_we_up_to()
    self.control_unit()

  def fetch(self):
    if self.PC < MemWords:
      return self.ram[self.PC << 2]
    if ROMStart <= self.PC < (ROMStart + len(self.rom)):
      PC = self.PC - ROMStart
      return self.rom[PC]
    raise ValueError(repr(self.PC))

  def decode(self, instruction):
    self.IR = IR = bint(instruction)
    self.p = IR[31]
    self.q = IR[30]
    self.u = IR[29]
    self.v = IR[28]
    self.w = IR[16]
    self.op = IR[20, 16]
    self.ira = IR[28, 24]
    self.irb = IR[24, 20]
    self.irc = IR[4, 0]
    self.cc = IR[27, 24]
    self.imm = IR[16, 0]
    self.off = IR[20, 0]
    self.jmp = IR[24, 0]
    self.C0 = self.R[self.irc]

  def what_are_we_up_to(self):
    self.MOV = (not self.p) and (self.op == 0)
    self.LSL = (not self.p) and (self.op == 1)
    self.ASR = (not self.p) and (self.op == 2)
    self.ROR = (not self.p) and (self.op == 3)
    self.AND = (not self.p) and (self.op == 4)
    self.ANN = (not self.p) and (self.op == 5)
    self.IOR = (not self.p) and (self.op == 6)
    self.XOR = (not self.p) and (self.op == 7)
    self.ADD = (not self.p) and (self.op == 8)
    self.SUB = (not self.p) and (self.op == 9)
    self.MUL = (not self.p) and (self.op == 10)
    self.DIV = (not self.p) and (self.op == 11)

    self.LDR = self.p and (not self.q) and (not self.u)
    self.STR = self.p and (not self.q) and self.u
    self.BR  = self.p and self.q

  def control_unit(self):
    if not self.p:
      self.register_instruction()
    elif self.q:
      self.branch_instruction()
    else:
      self.ram_instruction()

  def Arithmetic_Logical_Unit(self):
    B = self.R[self.irb]

    # Here's how negative immediate values are stored in the instruction and
    # regenerated in the cpu. In the ORGX module the instruction is created
    # like so:
    #
    #  PROCEDURE Put1(op, a, b, im: LONGINT);
    #  BEGIN (*emit format-1 instruction,  -10000H <= im < 10000H*)
    #    IF im < 0 THEN INC(op, 1000H) END ;  (*set v-bit*)
    #    code[pc] := (((a+40H) * 10H + b) * 10H + op) * 10000H + (im MOD 10000H); INC(pc)
    #  END Put1;
    #
    # If the immediate value is negative the V bit in the instruction is set.
    # In any event the immediate value has its high sixteen bits masked off
    # (modulus 0x10000 effects this.)  For example, -23 looks like this,
    # bit-wise:
    #
    #   11111111111111111111111111101001
    #
    # And after truncating the high bits:
    #
    #                   1111111111101001
    #
    # This is the bit pattern that gets stored in the instruction immediate
    # field.
    #
    # The statement immediately below reconstructs the negative 32-bit value
    # if the V bit is set in the instruction, otherwise it simply passes
    # through the given immediate value. (This happens, of coures, only if
    # the Q bit is set, otherwise C1 is just set to C0.)

    C1 = self.C1 = (
      (0b11111111111111110000000000000000 | self.imm)
      if self.v else
      self.imm
      ) if self.q else self.C0

    if self.MOV:
      # (q ? (~u ? {{16{v}}, imm} : {imm, 16'b0}) :
      if self.q:
        res = C1 if not self.u else (self.imm << 16)
      else:
        # (~u ? C0 : ... )) :
        if not self.u:
          res = self.C0
        else:
          # ... (~irc[0] ? H : {N, Z, C, OV, 20'b0, 8'b01010000})
          if not self.irc[0]:
            res = self.H
          else:
            res = (
              self.N << 31 |
              self.Z << 30 |
              self.C << 29 |
              self.OV << 28 |
              80
              )

    # Bit-wise logical operations

    elif self.LSL:
      res = B << C1
    elif self.ASR:
      res = B >> C1
      if bint(B)[31]: # Extend sign bit.
        res |= 2**C1 - 1 << (32 - C1)
    elif self.ROR:
      lost_bits = bint(B)[C1:0]
      res = (B >> C1) | (lost_bits << (32 - C1))
    elif self.AND:
      res = B & C1
    elif self.ANN:
      res = B & (F ^ C1)
    elif self.IOR:
      res = B | C1
    elif self.XOR:
      res = B ^ C1

    # For the arithmetical operators we must convert to Python ints to
    # correctly handle negative numbers.

    elif self.ADD:
      B = signed2py(B)
      C1 = signed2py(C1)
      res = B + C1 + (self.u and self.C)
      self.C = bool(res < B)
      res = self._check_overflow(res)

    elif self.SUB:
      B = signed2py(B)
      C1 = signed2py(C1)
      res = B - C1 - (self.u and self.C)
      res = self._check_overflow(res)
      self.C = bool(res > B)

    elif self.MUL:
      B = signed2py(B)
      C1 = signed2py(C1)
      product = B * C1
      self.product = blong(py2signed(product, 64))
      res = self.product[32:0]

    elif self.DIV:
      B = signed2py(B)
      C1 = signed2py(C1)
      res, remainder = divmod(B, C1)
      res = py2signed(res)
      self.remainder = py2signed(remainder)

    else:
      raise ValueError() # We should never get here!

    return res

  def _check_overflow(self, res, bits=33):
    try:
      return py2signed(res)
    except ValueError:
      self.OV = True
      return blong(py2signed(res, bits))[32:0]
    self.OV = False

  def register_instruction(self):
    self.pcnext = self.PC + 1
    regmux = self.Arithmetic_Logical_Unit()
    self.set_register(regmux)

  def set_register(self, value):
    value = value if isinstance(value, bint) else bint(value)
    self.R[self.ira] = value[32:0]
    self.N = value[31]
    self.Z = value == 0
    self.H = (self.product[64:32] if self.MUL
              else self.remainder if self.DIV
              else self.H)

  def branch_instruction(self):
    S = self.N ^ self.OV
    T = ((self.cc == 0) & self.N |
         (self.cc == 1) & self.Z |
         (self.cc == 2) & self.C |
         (self.cc == 3) & self.OV |
         (self.cc == 4) & (self.C|self.Z) |
         (self.cc == 5) & S |
         (self.cc == 6) & (S|self.Z) |
         (self.cc == 7)
         )
    if self.IR[27]:
      T = not T
    if not T:
      self.pcnext = self.PC + 1
      return

    if self.v: # Save link
      self.R[15] = (self.PC + 1) << 2

    if self.u:
      offset = signed2py(self.jmp, width=24)
      self.pcnext = int(offset + self.PC + 1)
    else:
      self.pcnext = self.C0 >> 2

  def ram_instruction(self):
    self.addr = addr = int(self.R[self.irb] + self.off)
    if addr >= IO_RANGE:
      self.io(addr - IO_RANGE)
    elif self.LDR:
      value = self.ram.get_byte(addr) if self.v else self.ram[addr]
      self.set_register(value)
    elif self.v:
      self.ram.put_byte(addr, self.R[self.ira] & 255)
    else:
      self.ram[addr] = self.R[self.ira]
    self.pcnext = self.PC + 1

  def io(self, port):
    device = self.io_ports.get(port)
    if not device:
      raise Trap('no device at port 0x%x (aka %i)' % (port, port))
    if self.LDR:
      self.set_register(device.read())
    else:
      device.write(self.R[self.ira])

  def dump_ram(self, location=None, number=10):
    if location is None:
      location = self.PC
    for i in range(location - number, location + number):
      h = '>' if i == location else ' '
      print h, hex(i), dis(self.ram[i << 2])

  def view(self):
    if self.PC >= MemSize:
      return
    kw = self.__dict__.copy()
    kw['A'] = self.R[self.ira]
    #print '- ' * 40
    print 'PC: 0x%(PC)04x ---' % kw, dis(int(self.IR))
    if self.STR:
      print '            Storing', '[0x%(addr)04x] <- R%(ira)i = 0x%(A)08x' % kw
    elif self.LDR:
      print '            Loading', 'R%(ira)i <- [0x%(addr)04x]' % kw
    # Print the registers.
##    for i in range(0, 16, 2):
##      reg0, reg1 = self.R[i], self.R[i + 1]
##      print 'R%-2i = 0x%-8x' % (i + 1, reg1),
##      print 'R%-2i = 0x%-8x' % (i, reg0)
##    print


_BYTE_MASKS = (
  0b11111111111111111111111100000000,
  0b11111111111111110000000011111111,
  0b11111111000000001111111111111111,
  0b00000000111111111111111111111111,
  )


class ByteAddressed32BitRAM(object):

  def __init__(self):
    self.store = {}

  def get(self, addr):
    word_addr, byte_offset = divmod(addr, 4)
    assert not byte_offset, repr(addr)
    try:
      value = self.store[word_addr]
    except KeyError:
      # Should we log this?
      value = self.store[word_addr] = 0
    return value

  __getitem__ = get

  def put(self, addr, word):
    assert 0 <= word <= F, repr(word)
    word_addr, byte_offset = divmod(addr, 4)
    assert not byte_offset, repr(addr)
    self.store[word_addr] = word

  __setitem__ = put

  def get_byte(self, addr):
    word_addr, byte_offset = divmod(addr, 4)
    word = self.store[word_addr]
    return (word >> (8 * byte_offset)) & 255

  def put_byte(self, addr, byte):
    if isinstance(byte, str):
      byte = ord(byte[:1])
    if not (0 <= byte < 256):
      raise ValueError("byte out of range: %i" % (byte,))

    word_addr, byte_offset = divmod(addr, 4)
    n = 8 * byte_offset # How many bits to shift.
    byte <<= n

    try: # Get the current memory contents, if any.
      word = self.store[word_addr]
    except KeyError: # nothing there yet so
      pass # just store shifted byte, or
    else: # merge word and shifted byte
      # AND mask with the memory word to clear the bits for the
      # pre-shifted byte and OR the result with it.
      byte |= word & _BYTE_MASKS[byte_offset]
    self.store[word_addr] = byte

  def __len__(self):
    return (4 * (1 + max(self.store))) if self.store else 0

  def __repr__(self):
    return pformat(self.store)


if __name__ == '__main__':
  from devices import LEDs, FakeSPI, Disk
  from bootloader import bootloader

  memory = ByteAddressed32BitRAM()
  disk = Disk('disk.img')
  risc_cpu = RISC(bootloader, memory)

  risc_cpu.io_ports[4] = LEDs()
  risc_cpu.io_ports[20] = fakespi = FakeSPI()
  risc_cpu.io_ports[16] = fakespi.data

  fakespi.register(1, disk)

  def cycle():
    while True:
      try:
        risc_cpu.cycle()
#        risc_cpu.view()
      except:
        risc_cpu.dump_ram()
        break

  cycle()
