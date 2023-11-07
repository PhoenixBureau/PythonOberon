# -*- coding: utf-8 -*-
#
#    Copyright © 2019, 2022 Simon Forman
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
# N.B. this is a file which is not improved by the black format tool.
#


POP = 'pop'

class Register:

    def __init__(self, index):
        self.index = index
        self.name = f'R{index}'

    def __le__(self, other):
        if other is POP or other == POP:
            print(f'POP({self.name})')
        elif isinstance(other, int):
            # TODO move_immediate_word_to_register
            print(f'Mov_imm({self.name}, {other})')
        elif isinstance(other, tuple):
            if len(other) == 3:
                op, arg0, arg1 = other
                print(f'{op}({self.name}, {arg0}, {arg1})')
            elif len(other) == 2:
                op, arg0 = other
                print(f'{op}({self.name}, {arg0})')
##        else:
##            print(f'Mov({self.name}, {other})')
        return self

    def __iadd__(self, other):
        if isinstance(other, int):
            print(f'Add_imm({self.name}, {self.name}, {other})')
        elif isinstance(other, Register):
            print(f'Add({self.name}, {self.name}, {other.name})')
        return self

    def __iand__(self, other):
        if isinstance(other, int):
            print(f'And_imm({self.name}, {self.name}, {other})')
        return self

    def __ilshift__(self, other):
        if isinstance(other, int):
            print(f'Lsl_imm({self.name}, {self.name}, {other})')
        return self

    def __imul__(self, other):
        if isinstance(other, int):
            print(f'Mul_imm({self.name}, {self.name}, {other})')
        return self

    def __isub__(self, other):
        if isinstance(other, int):
            print(f'Sub_imm({self.name}, {self.name}, {other})')
        return self

    def __rshift__(self, other):
        if isinstance(other, int):
            return 'Asr_imm', self.name, other

    def __sub__(self, other):
        if isinstance(other, int):
            return 'Sub_imm', self.name, other
        if isinstance(other, Register):
            return 'Sub', self.name, other.name


class Labeler:
    def __matmul__(self, other):
        print(f'label({other})')

l = Labeler()


class Rammy:

    def __getitem__(self, addr, op='Load'):
        if isinstance(addr, Register):
            return (op, addr.name)
        if isinstance(addr, slice):
            return self.__getitem__(addr.start, 'Load_byte')
        assert False, repr(addr)

    def __setitem__(self, addr, value):
        if isinstance(addr, Register):
            if isinstance(value, Register):
                print(f'Store({value.name}, {addr.name})')
        elif isinstance(addr, slice):
            if isinstance(value, Register):
                print(f'Store_byte({value.name}, {addr.start.name})')


ram = Rammy()

R0 = Register(0)
R1 = Register(1)
R2 = Register(2)
R7 = Register(7)


DISPLAY_START = 0xE7F00

R2 <= DISPLAY_START - 312 * 4

R0 <= POP
R1 -= ord('!')

R2 <= R1 >> 2
R2 *= 52
R0 += R2
R1 &= 0b11
R0 += R1

R1 <= POP
R2 <= DISPLAY_START
R1 += R2
R7 <= 767
R2 <= POP
R2 *= 13
R2 <= R7 - R2
R2 <<= 7
R1 += R2

R2 <= 13

l@ '_pchr_loop'


R7 <= ram[R0:]  # Use trailing colon to signal byte access.

ram[R1:] = R7

R0 += 4
R1 -= 128
R2 -= 1
