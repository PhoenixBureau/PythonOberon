import unittest
from ram import WordAddressed32BitRAM


class TestSequenceFunctions(unittest.TestCase):

    def setUp(self):
        self.seq = range(10)

    def test_shuffle(self):
        self.assertEqual(1, 1)


if __name__ == '__main__':
    unittest.main()

