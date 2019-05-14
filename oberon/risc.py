# -*- coding: utf-8 -*-
#
#    Copyright © 2019 Simon Forman
#
#    This file is part of PythonOberon
#
#    PythonOberon is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    PythonOberon is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with PythonOberon.  If not see <http://www.gnu.org/licenses/>.
#
'''

Emulated Hardware
========================================


'''
import pdb
from time import time
from struct import unpack
from pprint import pformat
from assembler import dis
from util import (
  bint, blong,
  python_int_to_signed_int,
  signed_int_to_python_int,
  )


IO_RANGE = 0x0FFFFFFC0
ROMStart = 0xFFFFF800 / 4
MemSize = 0x00180000
MemWords = MemSize / 4


def log(message, *args):
  pass
##  print message % args
##  print >> stderr, message % args


class Trap(Exception):
  pass


class RISC(object):
  '''
  The RISC processsor.
  
  This class is designed for ease of introspection rather than efficiency.
  '''

  def __init__(self, rom, ram, PC=ROMStart):
    self.rom = rom
    self.ram = ram
    self.PC = self.pcnext = PC
    self.R = [0] * 16
    self.H = 0
    self.N = self.Z = self.C = self.OV = False
    self.io_ports = {}
    self.switches = 0

  def cycle(self):
    '''Run one cycle of the processor.'''
    self.PC = self.pcnext
    self.decode(self.fetch())
    if not self.p:
      self.register_instruction()
    elif self.q:
      self.branch_instruction()
    else:
      self.ram_instruction()

  def fetch(self):
    '''
    Load an instruction from RAM or ROM and return it.  Raise
    :py:exc:`Trap` if ``PC`` goes out of bounds or if the machine
    enters a certain kind of infinite loop (this is a way for code
    running on the emulated chip to signal *HALT*.)
    '''
    if self.PC < MemWords:
      instruction = self.ram[self.PC << 2]
    elif ROMStart <= self.PC < (ROMStart + len(self.rom)):
      instruction = self.rom[self.PC - ROMStart]
    else:
      raise Trap('Fetch from bad address 0x%08x' % (self.PC,))

    if instruction == 0xe7ffffff: # REPEAT UNTIL False i.e. halt loop.
      raise Trap('REPEAT-UNTIL-False-ing')

    return instruction

  def decode(self, instruction):
    '''
    Decode the instruction and set various field and flag member values
    of the emulator object.
    '''
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

##    if self.PC < MemWords:
##      print self.brief_view()

  def register_instruction(self):
    '''
    Increment ``PC`` and set a register from the ALU.
    '''
    self.pcnext = self.PC + 1
    self.set_register(self.Arithmetic_Logical_Unit())

  def Arithmetic_Logical_Unit(self):
    '''
    Enact the ALU of the RISC chip.
    '''
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
    # through the given immediate value. (This happens, of course, only if
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
      res = B << (C1 & 31)

    elif self.ASR:
      C1 &= 31
      res = B >> C1
      if bint(B)[31]:
        res |= (2**C1 - 1) << (32 - C1) # Extend sign bit.

    elif self.ROR:
      C1 &= 31
      lost_bits = bint(B)[C1:0]
      res = (B >> C1) | (lost_bits << (32 - C1))

    elif self.AND:
      res = B & C1

    elif self.ANN:
      res = B & (0xffffffff ^ C1)

    elif self.IOR:
      res = B | C1

    elif self.XOR:
      res = B ^ C1

    # For the arithmetical operators we must convert to Python ints to
    # correctly handle negative numbers.

    elif self.ADD:
      B = signed_int_to_python_int(B)
      C1 = signed_int_to_python_int(C1)
      res = B + C1 + (self.u and self.C)
      self.C = res < B
      res = self._check_overflow(res)

    elif self.SUB:
      B = signed_int_to_python_int(B)
      C1 = signed_int_to_python_int(C1)
      res = B - C1 - (self.u and self.C)
      res = self._check_overflow(res)
      self.C = res > B

    elif self.MUL:
      B = signed_int_to_python_int(B)
      C1 = signed_int_to_python_int(C1)
      product = B * C1
      self.product = blong(python_int_to_signed_int(product, 64))
      res = self.product[32:0]

    elif self.DIV:
      B = signed_int_to_python_int(B)
      C1 = signed_int_to_python_int(C1)
      res, remainder = divmod(B, C1)
      res = python_int_to_signed_int(res)
      self.remainder = python_int_to_signed_int(remainder)

    else:
      raise Trap('We should never get here!')

    return res

  def _check_overflow(self, res, bits=33):
    try:
      return python_int_to_signed_int(res)
    except ValueError:
      self.OV = True
      return blong(python_int_to_signed_int(res, bits))[32:0]
    self.OV = False

  def set_register(self, value):
    '''
    Set ``A`` register and ``N``, ``Z``, and ``H``.
    '''
    value = value if isinstance(value, bint) else bint(value)
    self.R[self.ira] = value[32:0]
    self.N = value[31]
    self.Z = value == 0
    self.H = (self.product[64:32] if self.MUL
              else self.remainder if self.DIV
              else self.H)

  def branch_instruction(self):
    '''
    Branch instruction.
    '''
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
      offset = signed_int_to_python_int(self.jmp, width=24)
      self.pcnext = int(offset + self.PC + 1)
    else:
      self.pcnext = self.C0 >> 2

  def ram_instruction(self):
    '''
    RAM read/write instruction.
    '''
    self.addr = addr = int(self.R[self.irb] + self._sign_extend_offset())

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

  def _sign_extend_offset(self):
    off = bint(self.off & 0xfffff)
    if off[19]:
      off = signed_int_to_python_int(off | 0xfff00000)
    return off

  def io(self, port):
    '''
    I/O instruction.
    '''
    device = self.io_ports.get(port)
    if not device:
      raise Trap('no device at port 0x%x (aka %i)' % (port, port))
    if self.LDR:
      self.set_register(device.read())
    else:
      device.write(self.R[self.ira])

  def dump_ram(self, location=None, number=10):
    '''
    Debug function, print a disassembly of a span of RAM.
    '''
    if location is None:
      location = self.PC
    for i in range(location - number, location + number):
      h = '>' if i == location else ' '
      print h, hex(i), dis(self.ram[i << 2])

  def view(self):
    '''
    Debug function, print current instruction.
    '''
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

  def brief_view(self):
    '''
    Debug function, print crude state of chip.
    '''
    return ('0x%08x : 0x%08x'
            ' %i %i %i %i %i %i %i %i'
            ' %i %i %i %i %i %i %i'
            ' 0x%x'
            ) % (
              (self.PC, self.IR)
              + tuple(map(signed_int_to_python_int, self.R[:-1]))
              + (self.R[-1],)
              )


class ByteAddressed32BitRAM(object):
  '''
  Represent a 32-bit wide RAM chip that is byte-addressed.

  E.g. addresses 0-3 are the first four bytes, or one (32-bit) word.
  '''

  BYTE_MASKS = (
    0b11111111111111111111111100000000,
    0b11111111111111110000000011111111,
    0b11111111000000001111111111111111,
    0b00000000111111111111111111111111,
    )

  def __init__(self):
    # Use a dict rather than some array.  Might be woth exploring other
    # datastructures...
    self.store = {}

  def get(self, addr):
    '''
    Return a (32-bit) word.  Address must be word-aligned.
    '''
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
    '''
    Set a (32-bit) word.  Address must be word-aligned.
    '''
    word_addr, byte_offset = divmod(addr, 4)
    assert not byte_offset, repr(addr)
    self.store[word_addr] = word

  __setitem__ = put

  def get_byte(self, addr):
    '''
    Return a byte.  Address need not be word-aligned.
    '''
    word_addr, byte_offset = divmod(addr, 4)
    word = self.store[word_addr]
    return (word >> (8 * byte_offset)) & 255

  def put_byte(self, addr, byte):
    '''
    Set a byte.  Address need not be word-aligned.
    '''
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
      byte |= word & self.BYTE_MASKS[byte_offset]
    self.store[word_addr] = byte

  def __len__(self):
    return (4 * (1 + max(self.store))) if self.store else 0

  def __repr__(self):
    return pformat(self.store)


class Disk(object):
  '''
  Disk

  (I cribbed most of this from
  `pdewacht/oberon-risc-emu <https://github.com/pdewacht/oberon-risc-emu>`
  .  I'm not exactly sure how it works but it does work, well enough to
  load the Oberon OS from the disk image.)
  '''

  SECTOR_SIZE = 512
  SECTOR_SIZE_WORDS = SECTOR_SIZE / 4

  diskCommand, diskRead, diskWrite, diskWriting = range(4)

  def __init__(self, image_file):
    self.state = self.diskCommand

    self.rx_buf = [None] * self.SECTOR_SIZE_WORDS
    self.rx_idx = 0

    self.tx_buf = [None] * (self.SECTOR_SIZE_WORDS + 2)
    self.tx_cnt = 0
    self.tx_idx = 0

    self.file = image_file
    self.read_sector()
    self.offset = 0x80002 if self.tx_buf[0] == 0x9B1EA38D else 0

  def read(self):
    if self.tx_idx >= 0 and self.tx_idx < self.tx_cnt:
      log('disk_read from buffer 0x%x', self.tx_buf[self.tx_idx])
      return self.tx_buf[self.tx_idx]
    log('disk_read from default 0xFF')
    return 255

  def write(self, word):
    log('disk_write 0x%x', word)

    self.tx_idx += 1

    if self.state == self.diskCommand:
      if (0xff & word) == 0xff and self.rx_idx == 0:
        log('disk_write PASS 0x%x', word)
        return
      log('disk_write diskCommand 0x%x to rx_buf[%i]', word, self.rx_idx)
      self.rx_buf[self.rx_idx] = word
      self.rx_idx += 1
      if self.rx_idx == 6:
        ##  pdb.set_trace()
        self.run_command()
        self.rx_idx = 0

    elif self.state == self.diskRead:
      if self.tx_idx == self.tx_cnt:
        self.state = self.diskCommand
        log('disk_write diskRead -> diskCommand')
        self.tx_cnt = 0
        self.tx_idx = 0

    elif self.state == self.diskWrite:
      if word == 254:
        self.state = self.diskWriting
        log('disk_write diskWrite -> diskWriting')

    elif self.state == self.diskWriting:
      if self.rx_idx < 128:
        self.rx_buf[self.rx_idx] = word

      self.rx_idx += 1

      if self.rx_idx == 128:
        self.write_sector()

      if self.rx_idx == 130:
        self.tx_buf[0] = 5
        self.tx_cnt = 1
        self.tx_idx = -1
        self.rx_idx = 0
        self.state = self.diskCommand
        log('disk_write diskWriting -> diskCommand')

  def run_command(self):
    cmd, a, b, c, d = self.rx_buf[0:5]
    a, b, c, d = (n & 0xff for n in (a, b, c, d))
    arg = (a << 24) | (b << 16) | (c << 8) | d
    log('run_command ' + ' '.join(map(hex, (cmd, arg))))

    if cmd == 81:
      self.state = self.diskRead
      self.tx_buf[0] = 0
      self.tx_buf[1] = 254
      self._seek(arg)
      ##  pdb.set_trace()
      self.read_sector(2)
      self.tx_cnt = 2 + 128

    elif cmd == 88:
      self.state = self.diskWrite
      self._seek(arg)
      self.tx_buf[0] = 0
      self.tx_cnt = 1

    else:
      self.tx_buf[0] = 0
      self.tx_cnt = 1

    self.tx_idx = -1

  def _seek(self, arg):
    log('#' * 100)
    a = (arg - self.offset) * self.SECTOR_SIZE
    log('seeking to %i (0x%x)', arg, a)
    self.file.seek(a)
      
  def read_sector(self, into=0):
    data = self.file.read(self.SECTOR_SIZE)
    self.tx_buf[into:] = unpack('<128I', data)

  def write_sector(self):
    log('write sector %r', self.rx_buf)
    # data = pack('<128I', self.rx_buf)
    # self.file.write(data)


class Mouse(object):
  '''Mouse'''

  def __init__(self):
    self.value = 0

  def read(self):
    return self.value

  def write(self, word):
    raise NotImplementedError

  def set_coords(self, x, y):
    self.value = self.value & 0xff000000 | x | (y << 12)

  def button_up(self, n):
    assert 1 <= n <= 3, repr(n)
    self.value = self.value & (0xffffffff ^ (1 << (27 - n)))

  def button_down(self, n):
    assert 1 <= n <= 3, repr(n)
    self.value = self.value | (1 << (27 - n))


class Clock(object):
  '''clock'''

  def __init__(self, now=None):
    self.reset(now)

  def read(self):
    return self.time() - self.start_time

  def write(self, word): # RESERVED
    raise NotImplementedError

  def reset(self, now=None):
    self.start_time = now or self.time()

  def time(self):
    '''Return int time in ms.'''
    return int(round(1000 * time()))


class LEDs(object):
  '''LEDs'''

  def __init__(self):
    self.switches = 0

  def read(self):
    return self.switches

  def write(self, word):
    print 'LEDs', bin(word)[2:]


class FakeSPI(object):
  '''SPI'''

  def __init__(self):
    self.things = {}
    self.current_thing = None

    class DataControl(object):

      def read(inner):
        if self.current_thing:
          data = self.current_thing.read()
        else:
          data = 0xff
        log('FakeSPI Data Read: 0x%x', data)
        return data

      def write(inner, word):
        log('FakeSPI Data Write: 0x%x', word)
        if self.current_thing:
          self.current_thing.write(word)

    self.data = DataControl()

  def register(self, index, thing):
    self.things[index] = thing

  def read(self):
    log('FakeSPI Control Read: 0x1')
    return 1

  def write(self, word):
    log('FakeSPI Control Write: 0x%x', word)
    word %= 4
    try:
      self.current_thing = self.things[word]
      log('Setting SPI device to %s', self.current_thing)
    except KeyError:
      log('No SPI device %i', word)
      self.current_thing = None


class Serial(object):
  
  def __init__(self, input_file):
    self.input_file = input_file

    class SerialStatus(object):

      def read(inner):
        return 1

      def write(inner, word):
        2/0

    self.status = SerialStatus()


  def read(self):
    return ord(self.input_file.read(1))

  def write(self, word):
    1/0
