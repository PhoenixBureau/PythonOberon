import unittest
from ram import WordAddressed32BitRAM


class TestSequenceFunctions(unittest.TestCase):

  def setUp(self):
    self.ram = WordAddressed32BitRAM()

  def test_get_invalid_address(self):
    self.assertRaises(
      KeyError,
      self.ram.get,
      23,
      )

  def test_get_invalid_address_getattr(self):
    self.assertRaises(KeyError, lambda: self.ram[23])

  def test_put_word(self):
    self.ram[23] = 18
    self.assertEqual(self.ram[23], 18)


if __name__ == '__main__':
    unittest.main()

