import unittest, traceback
from mock import MagicMock
from risc import RISC, ByteAddressed32BitRAM


class TestRISC(unittest.TestCase):

  def setUp(self):
    self.ram = MagicMock(name='RAM')
    self.cpu = RISC(self.ram)

  def test_Mov_imm(self):
    # Mov_imm(8, 1)
    self.ram.__getitem__.return_value = 0b1001000000000000000000000000001
    self.cpu.cycle()
    self.assertEqual(1, self.cpu.R[8])

##  def test_what(self):
##    self.ram.__getitem__.return_value = 0
##    print
##
#    self.cpu.view() #  FIXME:
##    Traceback (most recent call last):
##      File "test_risc.py", line 15, in test_what
##        self.cpu.view()
##      File "risc.py", line 187, in view
##        kw['A'] = self.R[self.ira]
##    AttributeError: 'RISC' object has no attribute 'ira'
##
##    try:
##      self.cpu.cycle()
##    except:
##      traceback.print_exc()
##    self.cpu.view()
##    print self.ram.mock_calls
##    print '-' * 40


class TestByteAddressed32BitRAM(unittest.TestCase):

  def setUp(self):
    self.ram = ByteAddressed32BitRAM()

  def test_get_invalid_address(self):
    self.assertRaises(KeyError, self.ram.get, 24)

  def test_get_invalid_address_getattr(self):
    self.assertRaises(KeyError, lambda: self.ram[24])

  def test_put_word(self):
    self.ram[24] = 18
    self.assertEqual(self.ram[24], 18)

  def test_put_word_get_byte(self):
    n = 24
    self.ram[n] = 0xdeadbeef
    for i, byte in zip(
      reversed(range(n, n + 4)),
      (0xde, 0xad, 0xbe, 0xef),
      ):
      mem = self.ram.get_byte(i)
      self.assertEqual(byte, mem)

  def test_put_byte_get_word(self):
    n = 24
    for i, byte in zip(
      reversed(range(n, n + 4)),
      (0xde, 0xad, 0xbe, 0xef),
      ):
      self.ram.put_byte(i, byte)
    word = self.ram[n]
    self.assertEqual(0xdeadbeef, word)


if __name__ == '__main__':
  unittest.main()
