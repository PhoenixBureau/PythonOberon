from myhdl import intbv, concat
from util import ibv, bits2signed_int, signed
from disassembler import dis


class RISC(object):

  def __init__(self, ram, PC=0):
    self.ram = ram
    self.PC = self.pcnext = PC
    self.R = [0 for i in range(16)]
    self.H = 0
    self.N = self.Z = self.C = self.OV = 0

  def cycle(self):
    self.PC = self.pcnext
    instruction = self.ram.get(self.PC)
    print self.PC, repr(instruction)
    self.decode(instruction)
    self.what_are_we_up_to()
    self.control_unit()

  def decode(self, instruction):
    self.IR = IR = ibv(32, instruction)
    self.p, self.q, self.u, self.v, self.w = IR(31), IR(30), IR(29), IR(28), IR(16)
    self.op, self.ira, self.irb, self.irc = IR(20, 16), IR(28, 24), IR(24, 20), IR(4, 0)
    self.cc = IR(27, 24)
    self.imm = IR(16, 0)
    self.off = IR(20, 0)
    self.jmp = IR(24, 0)
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

    bits = 16 * [self.v] + [self.imm]
    C1 = self.C1 = concat(*bits) if self.q else self.C0

    if self.MOV:
      # (q ? (~u ? {{16{v}}, imm} : {imm, 16'b0}) :
      if self.q:
        res = C1 if not self.u else concat(self.imm, intbv(0)[16:])
      else:
        # (~u ? C0 : ... )) :
        if not self.u:
          res = self.C0
        else:
          # ... (~irc[0] ? H : {N, Z, C, OV, 20'b0, 8'b01010000})
          if not self.irc[0]:
            res = self.H
          else:
            res = concat(
              self.N, self.Z, self.C, self.OV,
              intbv(0)[20:],
              intbv(0b01010000),
              )
    elif self.LSL:
      res = B << C1
    elif self.ASR or self.ROR:
      res = B >> C1 # FIXME not quite right is it?
    elif self.AND:
      res = B and C1
    elif self.ANN:
      res = B and not C1
    elif self.IOR:
      res = B | C1
    elif self.XOR:
      res = B ^ C1
    elif self.ADD:
      x = B + C1 + (self.u and self.C)
      res = signed(x, 32)
    elif self.SUB:
      res = B - C1 - (self.u and self.C)
      res = signed(res, 32)
    elif self.MUL:
      self.product = intbv(B * C1)
      res = self.product[32:0]
    elif self.DIV:
      res = intbv(B / C1)
      self.remainder = B % C1
    else:
      res = 0

    return res if isinstance(res, intbv) else intbv(res)[32:0]

  def register_instruction(self):
    self.pcnext = self.PC + 4
    self.R[self.ira] = regmux = self.Arithmetic_Logical_Unit()
    self.N = regmux[31]
    self.Z = (regmux[31:0] == 0)
    self.C = regmux[32] if (self.ADD|self.SUB) else self.C
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
      self.pcnext = self.PC + 4
      return

    if self.v: # Save link
      self.R[15] = self.PC + 1

    if self.u:
      self.pcnext = int(self.jmp + self.PC + 4)
    elif self.IR[5]:
      self.pcnext = int(self.irc)
    else:
      self.pcnext = int(self.C0)

  def ram_instruction(self):
    self.addr = addr = int(self.R[self.irb] + self.off)
    if self.LDR:
      self.R[self.ira] = (self.ram.get_byte(addr) if self.v
                          else self.ram[addr])
    elif self.v:
      self.ram.put_byte(addr, self.R[self.ira] & 255)
    else:
      self.ram[addr] = self.R[self.ira]
    self.pcnext = self.PC + 4

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

####    for i in range(0, 16):
####      print '[%x]: 0x%x' % (i, _RAM[i])
####    print


if __name__ == '__main__':
  from ram import ByteAddressed32BitRAM
  from assembler import Mov_imm, Add, Lsl_imm, T_link

  memory = ByteAddressed32BitRAM()
  for addr, instruction in enumerate((
    Mov_imm(8, 1),
    Mov_imm(1, 1),
    Add(1, 1, 8),
    Lsl_imm(1, 1, 2),
    T_link(1),
    )):
    memory.put(addr * 4, int(instruction))

  risc_cpu = RISC(memory)
  for _ in range(10):
    risc_cpu.cycle()
    risc_cpu.view()

