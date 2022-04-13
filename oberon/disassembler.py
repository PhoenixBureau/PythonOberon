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
from oberon.assembler import cmps, opof, ops_rev
from oberon.util import bint

'''
while True:
    print(dis(int((2**32 - 1) * random.random())))
'''


def dis(n):
    '''
    Take an integer and return the assembly instruction.
    '''
    IR = bint(n)
    return INSTRUCTION_FORMATS[IR[32:30]](IR)


def dis_F0(IR):
    u, a, b, op, c = IR[29], IR[28:24], IR[24:20], IR[20:16], IR[4:0]
    if ops_rev[op] == 'Mov':
        value = dis_Mov0(u, IR[28], a, c)
    else:
        value = f'{opof(op)}({a}, {b}, {c}, u={u})'
    return value


def dis_Mov0(u, v, a, c):
    if u:
        if v:
            value = f'Mov({a}, 0, u={u}, v={v})  # R{a} <- (N,Z,C,OV, 0..01010000)'
        else:
            value = f'Mov({a}, 0, u={u}, v={v})  # R{a} <- H'
    else:
        value = f'Mov({a}, {c}, u={u})'
    return value


def dis_F1(IR):
    u, v, a, b, op, imm = IR[29], IR[28], IR[28:24], IR[24:20], IR[20:16], IR[16:0]
    if ops_rev[op] == 'Mov':
        value = f'Mov_imm({a}, 0x{imm:x}, u={u}, v={v})'
    else:
        value = f'{opof(op)}_imm({a}, {b}, 0x{imm:x}, u={u}, v={v})'
    return value


_ram_instrs = {
    # IR[29], IR[28]
    # u       v
    (True,   True): 'Store_byte',
    (True,  False): 'Store_word',
    (False,  True): 'Load_byte',
    (False, False): 'Load_word',
    }

def dis_F2(IR):
    u, v, a, b, off = IR[29], IR[28], IR[28:24], IR[24:20], IR[20:0]
    fn = _ram_instrs[u, v]
    if off:
        value = f'{fn}({a}, {b}, offset={hex(off)})'
    else:
        value = f'{fn}({a}, {b})'
    return value


def dis_F3(IR):
    op = cmps[int(IR[27:24]), int(IR[27])]  # I forget why int(...).
    u, v, c = IR[29], IR[28], IR[4:0]
    if not u:
        if v:
            value = f'{op}_link({c})'
        else:
            value = f'{op}({c})'
    else:
        off = int(IR[24:0])
        value = f'{op}_imm({hex(off)})'
    return value


INSTRUCTION_FORMATS = dis_F0, dis_F1, dis_F2, dis_F3
