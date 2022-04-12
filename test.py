import unittest

import assembler as asm
from disassembler import dis

source_lines = '''\
Mov_imm(0, 0x3333, v=False, u=True)
Ior_imm(0, 0, 0x3333, v=False, u=False)
Mov_imm(1, 0xf, v=False, u=True)
Ior_imm(1, 1, 0xfefc, v=False, u=False)
Mov_imm(2, 0x6000, v=False, u=False)
Store_word(0, 1)
Sub_imm(1, 1, 0x4, v=False, u=False)
Sub_imm(2, 2, 0x1, v=False, u=False)
NE_imm(-0x4)
T_imm(-0x1)
'''.splitlines()

class TestInstructions(unittest.TestCase):

    def _get_context(self):
        return {
            name: getattr(asm, name)
            for name in dir(asm)
            if not name.startswith('_')
            }

    def test_op(self):
        for code in source_lines:
            print(code)
            instruction = eval(code, self._get_context())
            disasm = dis(instruction)
            self.assertEqual(code, disasm)

##    def test_isupper(self):
##        self.assertTrue('FOO'.isupper())
##        self.assertFalse('Foo'.isupper())
##
##    def test_split(self):
##        s = 'hello world'
##        self.assertEqual(s.split(), ['hello', 'world'])
##        # check that s.split fails when the separator is not a string
##        with self.assertRaises(TypeError):
##            s.split(2)

if __name__ == '__main__':
    unittest.main()
