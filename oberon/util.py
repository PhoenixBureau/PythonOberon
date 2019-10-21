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

Utilities
=============================

'''
from math import log, floor
from struct import pack, unpack


class binary_addressing_mixin(object):
  '''
  Permit integers to be addressed bit-wise.

  Single indexing (foo[bar]) returns a Boolean value, while slicing
  returns an integer (foo[bar:baz]).  Slice indexes are left-to-right
  and do not support step parameter.
  '''

  def __getitem__(self, n):
    if isinstance(n, tuple):
      if len(n) != 2:
        raise IndexError('Must pass only two indicies.')
      start, stop = n
      return self._mask(stop, start - stop)

    if isinstance(n, slice):
      return self._getslice(n)

    return bool(self >> n & 1)

  def _getslice(self, s):
    if s.step:
      raise TypeError('Slice with step not supported.')

    start = 0 if s.start is None else s.start
    stop = 0 if s.stop is None else s.stop
    n = start - stop
    if n < 0:
      raise IndexError('Slice indexes should be left-to-right.')

    if not n:
      return type(self)(0)

    return self._mask(stop, n)

  def _mask(self, stop, n):
    return type(self)(self >> stop & (2**n - 1))


#class bint(binary_addressing_mixin, int): pass
class blong(binary_addressing_mixin, long): pass
bint = blong


def python_int_to_signed_int(i, width=32):
  '''
  Given a Python integer, possibly negative, return the Python integer
  that has the same bit pattern as the C signed int of the same value
  would have.

  I.e.:
    >>> n = -23
    >>> bin(n)
    '-0b10111'
    >>> n = python_int_to_signed_int(n)
    >>> bin(n)
    '0b11111111111111111111111111101001'
    >>> 
  
  '''
  assert width > 0
  width -= 1
  b = 2**width
  if not (-b <= i < b):
    raise ValueError
  if i >= 0:
    return i
  return b + i + (1 << width)


def signed_int_to_python_int(i, width=32):
  '''
  Convert a Python integer representing the bit-pattern of a C signed int
  into a Python integer of the same value.

  I.e.:
    >>> n = 0b11111111111111111111111111101001
    >>> n
    4294967273
    >>> n = 4294967273
    >>> bin(n)
    '0b11111111111111111111111111101001'
    >>> n = signed_int_to_python_int(n)
    >>> n
    -23

  '''
  assert width > 0
  b = 2**width
  if not (0 <= i < b):
    raise ValueError
  if i < b / 2:
    return i
  return i - b


# The following pair of functions do the same thing as the above pair,
# but only for values of thirty-two bits.


##def unsigned_to_signed(g):
##  return unpack('<i', pack('<I', g))[0]


##def signed_to_unsigned(g):
##  return unpack('<I', pack('<i', g))[0]


def signed(n, bits=16):
  limit = 2**bits
  if -limit < n < limit:
    q = ((n < 0) << (bits - 1)) + abs(n)
    return bint(q)[bits:]
  raise ValueError


##def bits2signed_int(i, n=32):
##  if not isinstance(i, bint):
##    raise ValueError("Must be bint object. %r" % (i,))
##  n -= 1
##  return (-1 if i[n] else 1) * i[n:]


##def encode_float(f):
##  return bits2signed_int(bint(unpack('>I', pack('>f', f))[0]))

##def decode_float(f):
##  return unpack('>f', pack('>I', signed(f, 32)))[0]

##def encode_set(s, size=32):
##  return sum(1 << n for n in range(size) if n in s)

##def decode_set(i, size=32):
##  w = bint(i)
##  return {n for n in range(size) if w[n]}


##def log2(x):
##  y = 0
##  while x > 1:
##    x /= 2
##    y += 1
##  return y


##def log2(x):
##  return int(floor(log(x, 2)))


##def word_print(it):
##  b = bin(it)[2:]
##  print (32 - len(b)) * '0' + b
