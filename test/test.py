# -*- coding: utf-8 -*-
#
#    Copyright © 2022 Simon Forman
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
import unittest

import oberon.assembler as asm
from oberon.disassembler import dis

source_lines = '''\
Mov_imm(0, 0x3333, u=True, v=False)
Ior_imm(0, 0, 0x3333, u=False, v=False)
Mov_imm(1, 0xf, u=True, v=False)
Ior_imm(1, 1, 0xfefc, u=False, v=False)
Mov_imm(2, 0x6000, u=False, v=False)
Store_word(0, 1)
Sub_imm(1, 1, 0x4, u=False, v=False)
Sub_imm(2, 2, 0x1, u=False, v=False)
NE_imm(0xffffc)
T_imm(0xfffff)
'''.splitlines()

class TestASM(unittest.TestCase):

    AST = {
        name: getattr(asm.ASM, name)
        for name in dir(asm.ASM)
        if not name.startswith('_')
        }

    def test_op(self):
        for code in source_lines:
            print(code)
            instruction = eval(code, self.AST.copy())
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
