from pprint import pformat
from myhdl import intbv
from util import ibv, bits2signed_int, signed
from assembler import dis
from signs import py2signed, signed2py


F = 2**32-1
IO_RANGE = 0x0FFFFFFC0


class Trap(Exception):
  pass


class RISC(object):

  MT = 12 # Module Table register.

  def __init__(self, ram, PC=0):
    self.ram = ram
    self.PC = self.pcnext = PC
    self.R = [0] * 16
    self.H = 0
    self.N = self.Z = self.C = self.OV = 0
    self.io_ports = {}

  def cycle(self):
    self.PC = self.pcnext
    instruction = self.ram[self.PC << 2]
    self.decode(instruction)
    self.what_are_we_up_to()
    self.control_unit()

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
      if self.pcnext == self.R[self.MT]:
        raise Trap(self.IR[8:4])
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
    # In any event the immediate value has it's high sixteen bits masked off
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
    elif self.ASR or self.ROR:
      res = B >> C1 # FIXME not quite right is it?
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
      res = self._check_overflow(res)

    elif self.SUB:
      B = signed2py(B)
      C1 = signed2py(C1)
      res = B - C1 - (self.u and self.C)
      res = self._check_overflow(res)

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
      res = 0

    return res if isinstance(res, bint) else bint(res)

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
    self.R[self.ira] = regmux[32:0]
    self.N = regmux[31]
    self.Z = regmux == 0
    if self.ADD | self.SUB:
      self.C = regmux[32]
#    self.OV = ... if (ADD|SUB) else OV
    self.H = (self.product[64:32] if self.MUL
              else self.remainder if self.DIV
              else self.H)

  def branch_instruction(self):
    S = self.N ^ self.OV
    if not (
      self.IR[27] ^
      ((self.cc == 0) & self.N |
       (self.cc == 1) & self.Z |
       (self.cc == 2) & self.C |
       (self.cc == 3) & self.OV |
       (self.cc == 4) & (self.C|self.Z) |
       (self.cc == 5) & S |
       (self.cc == 6) & (S|self.Z) |
       (self.cc == 7)
       )
      ):
      self.pcnext = self.PC + 1
      return

    if self.v: # Save link
      self.R[15] = self.PC + 1

    if self.u:
      self.pcnext = int(self.jmp + self.PC + 1)
    elif self.IR[5]:
      self.pcnext = int(self.irc)
    else:
      self.pcnext = int(self.C0)

  def ram_instruction(self):
    self.addr = addr = int(self.R[self.irb] + self.off)
    if addr >= IO_RANGE:
      self.io(addr - IO_RANGE)
    elif self.LDR:
      self.R[self.ira] = (self.ram.get_byte(addr) if self.v
                          else self.ram[addr])
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
      self.R[self.ira] = device.read()
    else:
      device.write(self.R[self.ira])

  def view(self):
    kw = self.__dict__.copy()
    kw['A'] = self.R[self.ira]
    print '- ' * 40
    print 'PC: [0x%(PC)04x] = 0x%(IR)08x =' % kw, dis(int(self.IR))
    print
    if self.STR:
      print 'Storing', '[0x%(addr)04x] <- R%(ira)i = 0x%(A)08x' % kw
      print
    elif self.LDR:
      print 'loading', 'R%(ira)i <- [0x%(addr)04x]' % kw
      print

    for i in range(0, 16, 2):
      reg0, reg1 = self.R[i], self.R[i + 1]
      print 'R%-2i = 0x%-8x' % (i + 1, reg1),
      print 'R%-2i = 0x%-8x' % (i, reg0)
    print


class ByteAddressed32BitRAM(object):

  def __init__(self):
    self.store = {}

  def get(self, addr):
    word_addr, byte_offset = divmod(addr, 4)
    assert not byte_offset, repr(addr)
    return self.store[word_addr]

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
      mask = F ^ (255 << n)
      # mask should now be one of:
      # 0b11111111111111111111111100000000
      # 0b11111111111111110000000011111111
      # 0b11111111000000001111111111111111
      # 0b00000000111111111111111111111111
      # Now AND the mask with the memory word to clear the bits for the
      # pre-shifted byte, and OR the result with same.
      byte |= word & mask
    self.store[word_addr] = byte

  def __len__(self):
    return (4 * (1 + max(self.store))) if self.store else 0

  def __repr__(self):
    return pformat(self.store)


class binary_addressing_mixin(object):

  def __getitem__(self, n):
    if isinstance(n, tuple):
      if len(n) != 2:
        raise IndexError('Must pass only two indicies.')
      start, stop = n
      return self._mask(stop, start - stop)
    if isinstance(n, slice):
      return self._getslice(n)
    return bool(self >> n & 1)

  def _getslice(self, s):
    n = s.start - s.stop
    if n < 0:
      raise IndexError('Slice indexes should be left-to-right.')
    if not n:
      raise IndexError('Zero bits.')
    if s.step:
      raise TypeError('Slice with step not supported.')

    return self._mask(s.stop, n)

  def _mask(self, stop, n):
    return type(self)(self >> stop & (2**n - 1))


class bint(binary_addressing_mixin, int): pass
class blong(binary_addressing_mixin, long): pass


if __name__ == '__main__':
##  from assembler import Mov_imm, Add, Lsl_imm, T_link
  from bootloader import bootloader

  memory = ByteAddressed32BitRAM()
  for addr, instruction in enumerate((
    bootloader
##    Mov_imm(8, 1),
##    Mov_imm(1, 1),
##    Add(1, 1, 8),
##    Lsl_imm(1, 1, 2),
##    T_link(1),
    )):
    memory.put(addr * 4, int(instruction))

  risc_cpu = RISC(memory)
  for _ in range(100):
    risc_cpu.cycle()
    risc_cpu.view()

