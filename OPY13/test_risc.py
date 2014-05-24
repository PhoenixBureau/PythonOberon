import unittest
from ram import ByteAddressed32BitRAM


class TestSequenceFunctions(unittest.TestCase):

  def setUp(self):
    self.ram = ByteAddressed32BitRAM()

  def test_get_invalid_address(self):
    self.assertRaises(
      KeyError,
      self.ram.get,
      24,
      )

  def test_get_invalid_address_getattr(self):
    self.assertRaises(KeyError, lambda: self.ram[24])

  def test_put_word(self):
    self.ram[24] = 18
    self.assertEqual(self.ram[24], 18)


if __name__ == '__main__':
    unittest.main()

