import unittest
from risc import ByteAddressed32BitRAM


class TestSequenceFunctions(unittest.TestCase):

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
