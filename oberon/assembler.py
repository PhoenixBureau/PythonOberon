# -*- coding: utf-8 -*-
#
#    Copyright © 2019 Simon Forman
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
'''

Assembler
=========================================

A very simple "assembler".  Really it's just a collection of routines to
generate binary order codes for debugging.

There's also a simple "disassembler" for Wirth RISC binary machine codes.
Currently only the crudest decoding is performed on a single instruction
(no extra information is used, in particular symbols are not supported.)
'''
from util import signed, bint, signed_int_to_python_int


ops = dict(
  Mov = 0, Lsl = 1, Asr = 2, Ror = 3,
  And = 4, Ann = 5, Ior = 6, Xor = 7,
  Add = 8, Sub = 9, Mul = 10, Div = 11,
  Fad = 12, Fsb = 13, Fml = 14, Fdv = 15,
  )
'Operation names mapped to their values in instructions.'

ops_rev = dict((v, k) for k, v in ops.iteritems())


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


def Mov(a, c, u=0): return make_F0(u, 0, a, 0, c)
def Lsl(a, b, c, u=0): return make_F0(u, 1, a, b, c)
def Asr(a, b, c, u=0): return make_F0(u, 2, a, b, c)
def Ror(a, b, c, u=0): return make_F0(u, 3, a, b, c)
def And(a, b, c, u=0): return make_F0(u, 4, a, b, c)
def Ann(a, b, c, u=0): return make_F0(u, 5, a, b, c)
def Ior(a, b, c, u=0): return make_F0(u, 6, a, b, c)
def Xor(a, b, c, u=0): return make_F0(u, 7, a, b, c)
def Add(a, b, c, u=0): return make_F0(u, 8, a, b, c)
def Sub(a, b, c, u=0): return make_F0(u, 9, a, b, c)
def Mul(a, b, c, u=0): return make_F0(u, 10, a, b, c)
def Div(a, b, c, u=0): return make_F0(u, 11, a, b, c)

def Mov_imm(a, K, v=0, u=0): return make_F1(u, v, 0, a, 0, K)
def Lsl_imm(a, b, K, v=0, u=0): return make_F1(u, v, 1, a, b, K)
def Asr_imm(a, b, K, v=0, u=0): return make_F1(u, v, 2, a, b, K)
def Ror_imm(a, b, K, v=0, u=0): return make_F1(u, v, 3, a, b, K)
def And_imm(a, b, K, v=0, u=0): return make_F1(u, v, 4, a, b, K)
def Ann_imm(a, b, K, v=0, u=0): return make_F1(u, v, 5, a, b, K)
def Ior_imm(a, b, K, v=0, u=0): return make_F1(u, v, 6, a, b, K)
def Xor_imm(a, b, K, v=0, u=0): return make_F1(u, v, 7, a, b, K)
def Add_imm(a, b, K, v=0, u=0): return make_F1(u, v, 8, a, b, K)
def Sub_imm(a, b, K, v=0, u=0): return make_F1(u, v, 9, a, b, K)
def Mul_imm(a, b, K, v=0, u=0): return make_F1(u, v, 10, a, b, K)
def Div_imm(a, b, K, v=0, u=0): return make_F1(u, v, 11, a, b, K)

def MI(c): return make_F3(0, c)
def PL(c): return make_F3(0, c, True)
def EQ(c): return make_F3(1, c)
def NE(c): return make_F3(1, c, True)
def CS(c): return make_F3(2, c)
def CC(c): return make_F3(2, c, True)
def VS(c): return make_F3(3, c)
def VC(c): return make_F3(3, c, True)
def LS(c): return make_F3(4, c)
def HI(c): return make_F3(4, c, True)
def LT(c): return make_F3(5, c)
def GE(c): return make_F3(5, c, True)
def LE(c): return make_F3(6, c)
def GT(c): return make_F3(6, c, True)
def T(c): return make_F3(7, c)
def F(c): return make_F3(7, c, True)

def MI_link(c): return make_F3(0, c, v=True)
def PL_link(c): return make_F3(0, c, True, True)
def EQ_link(c): return make_F3(1, c, v=True)
def NE_link(c): return make_F3(1, c, True, True)
def CS_link(c): return make_F3(2, c, v=True)
def CC_link(c): return make_F3(2, c, True, True)
def VS_link(c): return make_F3(3, c, v=True)
def VC_link(c): return make_F3(3, c, True, True)
def LS_link(c): return make_F3(4, c, v=True)
def HI_link(c): return make_F3(4, c, True, True)
def LT_link(c): return make_F3(5, c, v=True)
def GE_link(c): return make_F3(5, c, True, True)
def LE_link(c): return make_F3(6, c, v=True)
def GT_link(c): return make_F3(6, c, True, True)
def T_link(c): return make_F3(7, c, v=True)
def F_link(c): return make_F3(7, c, True, True)

#  ((cc == 0) & N | // MI, PL
#   (cc == 1) & Z | // EQ, NE
#   (cc == 2) & C | // CS, CC
#   (cc == 3) & OV | // VS, VC
#   (cc == 4) & (C|Z) | // LS, HI
#   (cc == 5) & S | // LT, GE
#   (cc == 6) & (S|Z) | // LE, GT
#   (cc == 7)); // T, F


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


def make_F1(u, v, op, a, b, K):
  assert bool(u) == u, repr(u)
  assert bool(v) == v, repr(v)
  assert ops['Mov'] <= op <= ops['Div'], repr(op)
  assert 0 <= a < 0x10, repr(a)
  assert 0 <= b < 0x10, repr(b)
  assert 0 <= abs(K) < 2**16, repr(K)
  return bint(
    (1 << 30) + # set q
    (u << 29) +
    (v << 28) +
    (a << 24) +
    (b << 20) +
    (op << 16) +
    signed(K)
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


def opof(op):
  return ops_rev[int(op)]
