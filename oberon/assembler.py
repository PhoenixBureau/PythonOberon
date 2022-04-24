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
'''

Assembler
=========================================

Miki Tebeka’s Clever Idea
http://pythonwise.blogspot.com/2012/06/python-based-assembler.html
https://raw.githubusercontent.com/tebeka/pythonwise/master/assembler.pdf


'''
from collections import defaultdict
from inspect import stack
from struct import pack
from pickle import dump

from oberon.util import bint, s_to_u_32


# Yes, friends, it's a global variable.
# I need to pass the file name down to the _debug_line() function for
# debuggin but that would involve passing it all the way down from
# assemble_file(), which would be a PITA.  So a harmless little global
# var is called for.
_filename = ''


def assemble_file(in_file, out_file, sym_file=None,
                  print_program=False,
                  epilog=None,  # Bytes to follow image
                  # in serial stream.  Not part of the program.
                  ):
    '''
    Accept up to three file objects.  The first is a source file,
    the second is the binary output file, and the optional third
    is a file to which to write symbols and other information
    (currently the other information is just a set of addresses
    that contain data, rather than machine code.)

    The symbol file is a pickle of a symbol table dictionary that
    maps label names to addresses, and the set of data addresses.

    The resulting binary file is suitable for loading over the
    serial port, you can pass it to the ``--serial-in`` command
    line option.

    This is the Oberon bootloader function that will load the
    binary over the serial line::

        PROCEDURE LoadFromLine;
          VAR len, adr, dat: INTEGER;
        BEGIN
          RecInt(len);
          WHILE len > 0 DO
            RecInt(adr);
            REPEAT
              RecInt(dat);
              SYSTEM.PUT(adr, dat);
              adr := adr + 4;
              len := len - 4
            UNTIL len = 0;
            RecInt(len)
          END
        END LoadFromLine;

    It reads a (4-byte) int length and drops into a while loop
    the loop reads a (4-byte) int address at which to store
    the following data.

    Then a second loop (repeat) is started to read the data.
    It reads a 4-byte word, stores it to the RAM, then
    increments the address and decrements the length (each by
    four.  So the length is counting bytes, not words!  N.B.)

    Once the repeat loop is done patching RAM it reads one more
    (4-byte) int length and the while loop restarts if the
    length is non-zero, otherwise we're done and the machine
    boots from there.

    '''
    global _filename
    _filename = in_file.name
    text = in_file.read()
    code = compile(text, in_file.name, 'exec')
    assembler = Assembler()
    program = assembler(code)
    program_list = [
        program.get(n, 0)  # Fill holes with zero.
        for n in range(0, max(program) + 4, 4)
        ]
    program_list.insert(0, len(program_list) * 4)
    program_list.insert(1, 0)  # address 0x00000000
    program_list.append(0)  # stop loading
    data = pack(f'<{len(program_list)}I', *program_list)
    out_file.write(data)
    if epilog:
        assert isinstance(epilog, bytes)
        while len(epilog) % 4: epilog += b'\x00'
        out_file.write(epilog)
    if sym_file:
        dump(
            (assembler.symbol_table, assembler.data_addrs),
            sym_file,
            )
    if print_program:
        assembler.print_program()


class DebugDict(dict):
    def __init__(self):
        dict.__init__(self)
        self.debug_info = defaultdict(list)

    def __setitem__(self, name, value):
        dict.__setitem__(self, name, value)
        self.debug_info[name].extend(self._debug_line())

    def print_debug(self, out=None):
        if out is None:
            import sys
            out = sys.stderr
        for addr, (frame, *frames) in sorted(self.debug_info.items()):
            lineno, line, function = frame
            function = f'(in {function})' if function != '<module>' else ''
            print(f'0x{addr:08x} line: {lineno} {line} {function}')
##            for lineno, line, function in frames:
##                print(f'           line: {lineno} {line} {function}')

    @staticmethod
    def _debug_line():
        global _filename
        return [(
            frame.lineno,
            frame.code_context[frame.index].rstrip(),
            frame.function
            ) for frame in stack()
            if frame.filename == _filename
            ]
    ##            #print(frame)
    ##            print(
    ##                f'{frame.lineno:3}'
    ##                f' {frame.code_context[frame.index].rstrip()[:60]:60}'
    ##                f' {frame.function}'
    ##                )


# pylint: disable=too-many-public-methods
class ASM:
    '''
    Collect the individual bit-pattern generator functions.
    '''
    # pylint: disable=invalid-name
    # pylint: disable=missing-function-docstring
    # pylint: disable=multiple-statements

    @staticmethod
    def Mov(a, c, u=0): return make_F0(u, 0, a, 0, c)
    @staticmethod
    def Mov_imm(a, K, v=0, u=0): return make_F1(u, v, 0, a, 0, K)

    # Arithmetic/Logic instructions

    @staticmethod
    def Lsl(a, b, c, u=0): return make_F0(u, 1, a, b, c)
    @staticmethod
    def Asr(a, b, c, u=0): return make_F0(u, 2, a, b, c)
    @staticmethod
    def Ror(a, b, c, u=0): return make_F0(u, 3, a, b, c)
    @staticmethod
    def And(a, b, c, u=0): return make_F0(u, 4, a, b, c)
    @staticmethod
    def Ann(a, b, c, u=0): return make_F0(u, 5, a, b, c)
    @staticmethod
    def Ior(a, b, c, u=0): return make_F0(u, 6, a, b, c)
    @staticmethod
    def Xor(a, b, c, u=0): return make_F0(u, 7, a, b, c)
    @staticmethod
    def Add(a, b, c, u=0): return make_F0(u, 8, a, b, c)
    @staticmethod
    def Sub(a, b, c, u=0): return make_F0(u, 9, a, b, c)
    @staticmethod
    def Mul(a, b, c, u=0): return make_F0(u, 10, a, b, c)
    @staticmethod
    def Div(a, b, c, u=0): return make_F0(u, 11, a, b, c)

    @staticmethod
    def Lsl_imm(a, b, K, v=0, u=0): return make_F1(u, v, 1, a, b, K)
    @staticmethod
    def Asr_imm(a, b, K, v=0, u=0): return make_F1(u, v, 2, a, b, K)
    @staticmethod
    def Ror_imm(a, b, K, v=0, u=0): return make_F1(u, v, 3, a, b, K)
    @staticmethod
    def And_imm(a, b, K, v=0, u=0): return make_F1(u, v, 4, a, b, K)
    @staticmethod
    def Ann_imm(a, b, K, v=0, u=0): return make_F1(u, v, 5, a, b, K)
    @staticmethod
    def Ior_imm(a, b, K, v=0, u=0): return make_F1(u, v, 6, a, b, K)
    @staticmethod
    def Xor_imm(a, b, K, v=0, u=0): return make_F1(u, v, 7, a, b, K)
    @staticmethod
    def Add_imm(a, b, K, v=0, u=0): return make_F1(u, v, 8, a, b, K)
    @staticmethod
    def Sub_imm(a, b, K, v=0, u=0): return make_F1(u, v, 9, a, b, K)
    @staticmethod
    def Mul_imm(a, b, K, v=0, u=0): return make_F1(u, v, 10, a, b, K)
    @staticmethod
    def Div_imm(a, b, K, v=0, u=0): return make_F1(u, v, 11, a, b, K)

    #  RAM instructions

    @staticmethod
    def Load_word(a, b, offset=0): return make_F2(0, 0, a, b, offset)
    @staticmethod
    def Load_byte(a, b, offset=0): return make_F2(0, 1, a, b, offset)
    @staticmethod
    def Store_word(a, b, offset=0): return make_F2(1, 0, a, b, offset)
    @staticmethod
    def Store_byte(a, b, offset=0): return make_F2(1, 1, a, b, offset)

    #  Branch instructions

    @staticmethod
    def MI(c): return make_F3(0, c)
    @staticmethod
    def PL(c): return make_F3(0, c, True)
    @staticmethod
    def EQ(c): return make_F3(1, c)
    @staticmethod
    def NE(c): return make_F3(1, c, True)
    @staticmethod
    def CS(c): return make_F3(2, c)
    @staticmethod
    def CC(c): return make_F3(2, c, True)
    @staticmethod
    def VS(c): return make_F3(3, c)
    @staticmethod
    def VC(c): return make_F3(3, c, True)
    @staticmethod
    def LS(c): return make_F3(4, c)
    @staticmethod
    def HI(c): return make_F3(4, c, True)
    @staticmethod
    def LT(c): return make_F3(5, c)
    @staticmethod
    def GE(c): return make_F3(5, c, True)
    @staticmethod
    def LE(c): return make_F3(6, c)
    @staticmethod
    def GT(c): return make_F3(6, c, True)
    @staticmethod
    def T(c): return make_F3(7, c)
    @staticmethod
    def F(c): return make_F3(7, c, True)

    @staticmethod
    def MI_link(c): return make_F3(0, c, v=True)
    @staticmethod
    def PL_link(c): return make_F3(0, c, True, True)
    @staticmethod
    def EQ_link(c): return make_F3(1, c, v=True)
    @staticmethod
    def NE_link(c): return make_F3(1, c, True, True)
    @staticmethod
    def CS_link(c): return make_F3(2, c, v=True)
    @staticmethod
    def CC_link(c): return make_F3(2, c, True, True)
    @staticmethod
    def VS_link(c): return make_F3(3, c, v=True)
    @staticmethod
    def VC_link(c): return make_F3(3, c, True, True)
    @staticmethod
    def LS_link(c): return make_F3(4, c, v=True)
    @staticmethod
    def HI_link(c): return make_F3(4, c, True, True)
    @staticmethod
    def LT_link(c): return make_F3(5, c, v=True)
    @staticmethod
    def GE_link(c): return make_F3(5, c, True, True)
    @staticmethod
    def LE_link(c): return make_F3(6, c, v=True)
    @staticmethod
    def GT_link(c): return make_F3(6, c, True, True)
    @staticmethod
    def T_link(c): return make_F3(7, c, v=True)
    @staticmethod
    def F_link(c): return make_F3(7, c, True, True)

    @staticmethod
    def MI_imm(offset): return make_F3_imm(0, offset)
    @staticmethod
    def PL_imm(offset): return make_F3_imm(0, offset, True)
    @staticmethod
    def EQ_imm(offset): return make_F3_imm(1, offset)
    @staticmethod
    def NE_imm(offset): return make_F3_imm(1, offset, True)
    @staticmethod
    def CS_imm(offset): return make_F3_imm(2, offset)
    @staticmethod
    def CC_imm(offset): return make_F3_imm(2, offset, True)
    @staticmethod
    def VS_imm(offset): return make_F3_imm(3, offset)
    @staticmethod
    def VC_imm(offset): return make_F3_imm(3, offset, True)
    @staticmethod
    def LS_imm(offset): return make_F3_imm(4, offset)
    @staticmethod
    def HI_imm(offset): return make_F3_imm(4, offset, True)
    @staticmethod
    def LT_imm(offset): return make_F3_imm(5, offset)
    @staticmethod
    def GE_imm(offset): return make_F3_imm(5, offset, True)
    @staticmethod
    def LE_imm(offset): return make_F3_imm(6, offset)
    @staticmethod
    def GT_imm(offset): return make_F3_imm(6, offset, True)
    @staticmethod
    def T_imm(offset): return make_F3_imm(7, offset)
    @staticmethod
    def F_imm(offset): return make_F3_imm(7, offset, True)


ops = dict(
    Mov = 0, Lsl = 1, Asr = 2, Ror = 3,
    And = 4, Ann = 5, Ior = 6, Xor = 7,
    Add = 8, Sub = 9, Mul = 10, Div = 11,
    Fad = 12, Fsb = 13, Fml = 14, Fdv = 15,
    )
'Operation names mapped to their values in instructions.'

ops_rev = dict((v, k) for k, v in ops.items())


##  ((cc == 0) & N | // MI, PL
##   (cc == 1) & Z | // EQ, NE
##   (cc == 2) & C | // CS, CC
##   (cc == 3) & OV | // VS, VC
##   (cc == 4) & (C|Z) | // LS, HI
##   (cc == 5) & S | // LT, GE
##   (cc == 6) & (S|Z) | // LE, GT
##   (cc == 7)); // T, F

cmps = {
    (0, 0): 'MI',
    (0, 1): 'PL',
    (1, 0): 'EQ',
    (1, 1): 'NE',
    (2, 0): 'CS',
    (2, 1): 'CC',
    (3, 0): 'VS',
    (3, 1): 'VC',
    (4, 0): 'LS',
    (4, 1): 'HI',
    (5, 0): 'LT',
    (5, 1): 'GE',
    (6, 0): 'LE',
    (6, 1): 'GT',
    (7, 0): 'T',
    (7, 1): 'F',
}


# pylint: disable=invalid-name, missing-function-docstring
def make_F0(u, op, a, b, c):
    assert bool(u) == u, repr(u)
    assert ops['Mov'] <= op <= ops['Div'], repr(op)
    assert 0 <= a < 0x10, repr(a)
    assert 0 <= b < 0x10, repr(b)
    assert 0 <= c < 0x10, repr(c)
    return bint(
        (u << 29) +
        (a << 24) +
        (b << 20) +
        (op << 16) +
        c
        )


# pylint: disable=too-many-arguments
def make_F1(u, v, op, a, b, K):
    assert bool(u) == u, repr(u)
    assert bool(v) == v, repr(v)
    assert ops['Mov'] <= op <= ops['Div'], repr(op)
    assert 0 <= a < 0x10, repr(a)
    assert 0 <= b < 0x10, repr(b)
    assert 0 <= K < 2**16, repr(K)
    return bint(
        (1 << 30) + # set q
        (u << 29) +
        (v << 28) +
        (a << 24) +
        (b << 20) +
        (op << 16) +
        K
        )


def make_F2(u, v, a, b, offset):
    assert bool(u) == u, repr(u)
    assert bool(v) == v, repr(v)
    assert 0 <= a < 0x10, repr(a)
    assert 0 <= b < 0x10, repr(b)
    assert 0 <= offset < 2**20, repr(offset)
    return bint(
        (1 << 31) +
        (u << 29) +
        (v << 28) +
        (a << 24) +
        (b << 20) +
        offset
        )


def make_F3(cond, c, invert=False, v=False):
    # v = True -> PC to be stored in register R15
    assert 0 <= cond < 0x111, repr(cond)
    assert 0 <= c < 0x10, repr(c)
    assert bool(invert) == invert, repr(invert)
    assert bool(v) == v, repr(v)
    return bint(
        (0b11 << 30) + # set p, q
        (v << 28) +
        (invert << 27) +
        (cond << 24) +
        c
        )


def make_F3_imm(cond, offset, invert=False, v=False):
    # v = True -> PC to be stored in register R15
    assert 0 <= cond < 0x111, repr(cond)
    assert 0 <= offset < 2**24, repr(offset)
    assert bool(invert) == invert, repr(invert)
    assert bool(v) == v, repr(v)
    return bint(
        (0b111 << 29) + # set p, q, u
        (v << 28) +
        (invert << 27) +
        (cond << 24) +
        offset
        )


def opof(op):
    return ops_rev[int(op)]


class LabelThunk:
    '''
    Stand for an address that will be determined later.
    '''
    # pylint: disable=too-few-public-methods

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f'<LabelThunk {self.name}>'


class Context(dict):
    '''
    Execution namespace for asm code.
    '''

    def __init__(self, symbol_table):
        dict.__init__(self)
        self.symbol_table = symbol_table

    def __setitem__(self, name, value):
        if name in self.symbol_table:
            it = self.symbol_table[name]
            if isinstance(it, LabelThunk):
                self.symbol_table[name] = value
            else:
                raise RuntimeError(f"Can't reassign labels: {name}")
        dict.__setitem__(self, name, value)

    def __getitem__(self, name):
        try:
            return dict.__getitem__(self, name)
        except KeyError:
            # print('# New unassigned label:', name)
            thunk = self[name] = self.symbol_table[name] = LabelThunk(name)
            return thunk


def deco(method):
    '''
    Wrap a method that uses ASM.*() to make bits.
    '''
    bits_maker = getattr(ASM, method.__name__)

    def wrapper(self, a, b, K, v=0, u=0):

        if isinstance(K, LabelThunk):

            # For thunks build a function to do fix up.
            def fixup(value):
                wrapper(self, a, b, value, v, u)

            instruction = (fixup,)
            self.fixups[K].append(self.here)

        else:  # Otherwise just make the bits now.
            instruction = bits_maker(a, b, K, v=v, u=u)

        self.program[self.here] = instruction
        self.here += 4

    return wrapper


def deco0(bits_maker):  # Wrap a method that uses ASM.*() to make bits.

    def inner(_method):

        def wrapper(self, offset):

            if isinstance(offset, LabelThunk):

                def fixup(value):
                    wrapper(self, value)
                instruction = (fixup,)
                self.fixups[offset].append(self.here)

            else:
                if offset % 4:
                    raise RuntimeError(f'bad offset {offset:x}')
                offset = (offset - self.here) // 4 - 1
                if offset < 0:
                    offset = s_to_u_32(offset) & 0xffffff # 2**24 -1
                instruction = bits_maker(offset)

            self.program[self.here] = instruction
            self.here += 4

        return wrapper

    return inner


class Assembler:
    '''
    Assembler
    '''

    def __init__(self):
        self.program = DebugDict()
        self.symbol_table = {}
        self.data_addrs = set()
        self.fixups = defaultdict(list)
        self.here = 0

        self.context = Context(self.symbol_table)
        # wtf w/ builtins?
        self.context['print'] = print
        self.context['len'] = len
        self.context['ord'] = ord
        self.context['globals'] = globals
        self.context['bytes'] = bytes
        self.context['range'] = range
        self.context['isinstance'] = isinstance

        for name in dir(Assembler):
            if not name.startswith('_'):
                value = getattr(self, name)
                if callable(value):
                    self.context[name] = value

    def print_program(self):
        # pylint: disable=import-outside-toplevel
        from oberon.disassembler import dis
        max_label_length = max(map(len, self.symbol_table))
        blank_prefix = ' ' * (2 + max_label_length)
        addrs_to_labels = {
            addr: label
            for label, addr in self.symbol_table.items()
            }
        for addr in range(0, max(self.program) + 4, 4):
            try:
                label = addrs_to_labels[addr]
            except KeyError:
                prefix = blank_prefix
            else:
                prefix = ' ' * (max_label_length - len(label)) + label + ': '
            if addr not in self.program:
                print(f'{prefix}0x{addr:05x} 0x00000000')
                continue
            i = self.program[addr]
            if addr in self.data_addrs:
                print(f'{prefix}0x{addr:05x} 0x{i:08x}')
                continue
            print(f'{prefix}0x{addr:05x} {dis(i)}')

    def __call__(self, text):
        # pylint: disable=exec-used
        exec(text, self.context)
        del self.context['__builtins__']
        self.program.print_debug()
        return self.program

    def dw(self, data):
        '''
        Lay in a data word literal value.
        Adds the current address to the ``data_addrs`` set
        attribute.
        '''
        if isinstance(data, LabelThunk):
            self.fixups[data].append(self.here)
            def fixup(value, h=self.here):
                assert 0 <= value < 2**32, repr(value)
                self.program[h] = value
            self.program[self.here] = (fixup,)
        else:
            assert 0 <= data < 2**32, repr(data)
            self.program[self.here] = data
        self.data_addrs.add(self.here)
        self.here += 4

    def HERE(self):
        '''
        Return the current address.
        '''
        return self.here

    def label(self, thunk, reserves=0):
        '''
        Enter a label in the symbol table, fix up any prior
        references to this label, and optionally reserve some
        RAM (``reserves`` counts bytes, not words, and can
        only reserve whole words to maintain alignment, so
        this must be a multiple of four.)
        '''
        if not isinstance(thunk, LabelThunk):
            raise RuntimeError('already assigned')
        self.context[thunk.name] = self.here
        self._fix(thunk, self.here)
        if reserves:
            assert reserves > 0, repr(reserves)
            assert 0 == (reserves % 4), repr(reserves)
            self.here += reserves

    def _fix(self, thunk, value):
        if thunk in self.fixups: # defaultdict!
            for addr in self.fixups.pop(thunk):
                fix = self.program[addr][0]
                # print('# fixing', thunk, 'at', hex(addr), 'to', hex(value), 'using', fix)
                temp, self.here = self.here, addr
                try:
                    fix(value)
                finally:
                    self.here = temp

    #==------------------------------------------------------------------
    #  Move instructions

    def Mov(self, a, c, u=0):
        self.program[self.here] = ASM.Mov(a, c, u)
        self.here += 4

    def Mov_imm(self, a, K, v=0, u=0):
        if isinstance(K, LabelThunk):
            self.fixups[K].append(self.here)
            def fixup(value, h=self.here):
                self.program[h] = ASM.Mov_imm(a, value, v, u)
            self.program[self.here] = (fixup,)
        else:
            self.program[self.here] = ASM.Mov_imm(a, K, v, u)
        self.here += 4

    #==------------------------------------------------------------------
    #  RAM instructions

    def Load_byte(self, a, b, offset=0):
        self.program[self.here] = ASM.Load_byte(a, b, offset)
        self.here += 4

    def Load_word(self, a, b, offset=0):
        self.program[self.here] = ASM.Load_word(a, b, offset)
        self.here += 4

    def Store_byte(self, a, b, offset=0):
        self.program[self.here] = ASM.Store_byte(a, b, offset)
        self.here += 4

    def Store_word(self, a, b, offset=0):
        self.program[self.here] = ASM.Store_word(a, b, offset)
        self.here += 4

    #==------------------------------------------------------------------
    #  Arithmetic/Logic instructions

    def Add(self, a, b, c, u=0):
        self.program[self.here] = ASM.Add(a, b, c, u)
        self.here += 4

    @deco
    def Add_imm(self, a, b, K, v=0, u=0):
        pass

    def And(self, a, b, c, u=0):
        self.program[self.here] = ASM.And(a, b, c, u)
        self.here += 4

    @deco
    def And_imm(self, a, b, K, v=0, u=0):
        pass

    def Ann(self, a, b, c, u=0):
        self.program[self.here] = ASM.Ann(a, b, c, u)
        self.here += 4

    @deco
    def Ann_imm(self, a, b, K, v=0, u=0):
        pass

    def Asr(self, a, b, c, u=0):
        self.program[self.here] = ASM.Asr(a, b, c, u)
        self.here += 4

    @deco
    def Asr_imm(self, a, b, K, v=0, u=0):
        pass

    def Div(self, a, b, c, u=0):
        self.program[self.here] = ASM.Div(a, b, c, u)
        self.here += 4

    @deco
    def Div_imm(self, a, b, K, v=0, u=0):
        pass

    def Ior(self, a, b, c, u=0):
        self.program[self.here] = ASM.Ior(a, b, c, u)
        self.here += 4

    @deco
    def Ior_imm(self, a, b, K, v=0, u=0):
        pass

    def Lsl(self, a, b, c, u=0):
        self.program[self.here] = ASM.Lsl(a, b, c, u)
        self.here += 4

    @deco
    def Lsl_imm(self, a, b, K, v=0, u=0):
        pass

    def Mul(self, a, b, c, u=0):
        self.program[self.here] = ASM.Mul(a, b, c, u)
        self.here += 4

    @deco
    def Mul_imm(self, a, b, K, v=0, u=0):
        pass

    def Ror(self, a, b, c, u=0):
        self.program[self.here] = ASM.Ror(a, b, c, u)
        self.here += 4

    @deco
    def Ror_imm(self, a, b, K, v=0, u=0):
        pass

    def Sub(self, a, b, c, u=0):
        self.program[self.here] = ASM.Sub(a, b, c, u)
        self.here += 4

    @deco
    def Sub_imm(self, a, b, K, v=0, u=0):
        pass

    def Xor(self, a, b, c, u=0):
        self.program[self.here] = ASM.Xor(a, b, c, u)
        self.here += 4

    @deco
    def Xor_imm(self, a, b, K, v=0, u=0):
        pass

    #==------------------------------------------------------------------
    #  Branch instructions

    def CC(self, c):
        self.program[self.here] = ASM.CC(c)
        self.here += 4

    @deco0(ASM.CC_imm)
    def CC_imm(self, offset):
        pass

    def CC_link(self, c):
        self.program[self.here] = ASM.CC_link(c)
        self.here += 4

    def CS(self, c):
        self.program[self.here] = ASM.CS(c)
        self.here += 4

    @deco0(ASM.CS_imm)
    def CS_imm(self, offset):
        pass

    def CS_link(self, c):
        self.program[self.here] = ASM.CS_link(c)
        self.here += 4

    def EQ(self, c):
        self.program[self.here] = ASM.EQ(c)
        self.here += 4

    @deco0(ASM.EQ_imm)
    def EQ_imm(self, offset):
        pass

    def EQ_link(self, c):
        self.program[self.here] = ASM.EQ_link(c)
        self.here += 4

    def F(self, c):
        self.program[self.here] = ASM.F(c)
        self.here += 4

    @deco0(ASM.F_imm)
    def F_imm(self, offset):
        pass

    def F_link(self, c):
        self.program[self.here] = ASM.F_link(c)
        self.here += 4

    def GE(self, c):
        self.program[self.here] = ASM.GE(c)
        self.here += 4

    @deco0(ASM.GE_imm)
    def GE_imm(self, offset):
        pass

    def GE_link(self, c):
        self.program[self.here] = ASM.GE_link(c)
        self.here += 4

    def GT(self, c):
        self.program[self.here] = ASM.GT(c)
        self.here += 4

    @deco0(ASM.GT_imm)
    def GT_imm(self, offset):
        pass

    def GT_link(self, c):
        self.program[self.here] = ASM.GT_link(c)
        self.here += 4

    def HI(self, c):
        self.program[self.here] = ASM.HI(c)
        self.here += 4

    @deco0(ASM.HI_imm)
    def HI_imm(self, offset):
        pass

    def HI_link(self, c):
        self.program[self.here] = ASM.HI_link(c)
        self.here += 4

    def LE(self, c):
        self.program[self.here] = ASM.LE(c)
        self.here += 4

    @deco0(ASM.LE_imm)
    def LE_imm(self, offset):
        pass

    def LE_link(self, c):
        self.program[self.here] = ASM.LE_link(c)
        self.here += 4

    def LS(self, c):
        self.program[self.here] = ASM.LS(c)
        self.here += 4

    @deco0(ASM.LS_imm)
    def LS_imm(self, offset):
        pass

    def LS_link(self, c):
        self.program[self.here] = ASM.LS_link(c)
        self.here += 4

    def LT(self, c):
        self.program[self.here] = ASM.LT(c)
        self.here += 4

    @deco0(ASM.LT_imm)
    def LT_imm(self, offset):
        pass

    def LT_link(self, c):
        self.program[self.here] = ASM.LT_link(c)
        self.here += 4

    def MI(self, c):
        self.program[self.here] = ASM.MI(c)
        self.here += 4

    @deco0(ASM.MI_imm)
    def MI_imm(self, offset):
        pass

    def MI_link(self, c):
        self.program[self.here] = ASM.MI_link(c)
        self.here += 4

    def NE(self, c):
        self.program[self.here] = ASM.NE(c)
        self.here += 4

    @deco0(ASM.NE_imm)
    def NE_imm(self, offset):
        pass

    def NE_link(self, c):
        self.program[self.here] = ASM.NE_link(c)
        self.here += 4

    def PL(self, c):
        self.program[self.here] = ASM.PL(c)
        self.here += 4

    @deco0(ASM.PL_imm)
    def PL_imm(self, offset):
        pass

    def PL_link(self, c):
        self.program[self.here] = ASM.PL_link(c)
        self.here += 4

    def T(self, c):
        self.program[self.here] = ASM.T(c)
        self.here += 4

    @deco0(ASM.T_imm)
    def T_imm(self, offset):
        pass

    def T_link(self, c):
        self.program[self.here] = ASM.T_link(c)
        self.here += 4

    def VC(self, c):
        self.program[self.here] = ASM.VC(c)
        self.here += 4

    @deco0(ASM.VC_imm)
    def VC_imm(self, offset):
        pass

    def VC_link(self, c):
        self.program[self.here] = ASM.VC_link(c)
        self.here += 4

    def VS(self, c):
        self.program[self.here] = ASM.VS(c)
        self.here += 4

    @deco0(ASM.VS_imm)
    def VS_imm(self, offset):
        pass

    def VS_link(self, c):
        self.program[self.here] = ASM.VS_link(c)
        self.here += 4
