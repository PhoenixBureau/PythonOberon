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

Display
========================

This module encapsulates the PyGame library and provides a mixin class
:py:class:`ScreenRAMMixin` for the :py:class:`oberon.risc.ByteAddressed32BitRAM`
class that visualizes the memory-mapped raster display on a PyGame surface.

'''
from sys import stderr
try:
  import pygame
  from pygame.locals import *

except ImportError:
  print >> stderr, 'Unable to import pygame.'


  class FakeScreen:
    '''
    If PyGame is unavailable this class will be used to imitate the 
    screen object.
    '''
    def set_at(self, (x, y), color):
      pass
  #    print x, y, color


  def initialize_screen():
    '''
    Pretend to initialize screen but just return a :py:obj:`FakeScreen`
    object.
    '''
    
    return FakeScreen()


  def display_flip():
    '''Pretend to flip the screen.'''
    pass


  class ScreenRAMMixin(object):
    '''
    A fake mixin class for :py:class:`ScreenRAMMixin`.
    '''
    def set_screen(self, screen):
      screen_size_hack(self)


else:


  def initialize_screen():
    '''
    Fire up PyGame and return a screen surface of :py:obj:`SIZE`.
    '''
    pygame.init()
    return pygame.display.set_mode(SIZE, 0, 8)


  def display_flip():
    '''
    Call ``pygame.display.flip()``.
    '''
    pygame.display.flip()


  class ScreenRAMMixin(object):
    '''
    A mixin class for the :py:class:`oberon.risc.ByteAddressed32BitRAM`
    that updates the PyGame screen pixels when data are written to RAM
    addresses within the memory-mapped raster display.
    '''

    def set_screen(self, screen):
      '''
      Connect a PyGame surface to the RAM.
      '''
      self.screen = screen
      screen_size_hack(self)

    def put(self, address, word):
      '''
      Extends :py:meth:`oberon.risc.ByteAddressed32BitRAM.put` to check
      for writes to the memory-mapped raster display RAM and update the
      PyGame screen accordingly.
      '''
      super(ScreenRAMMixin, self).put(address, word)
      if DISPLAY_START <= address < DISPLAY_START + DISPLAY_SIZE_IN_BYTES:
        # Convert byte RAM address to word screen address.
        address = (address - DISPLAY_START) >> 2
        update_screen(self.screen, address, word)

    def __setitem__(self, key, value):
      self.put(key, value)


SIZE = width, height = 1024, 768
'Size of the screen in pixels.'

DISPLAY_START = 0xe7f00
'RAM address of the start of the memory-mapped raster display.'

DISPLAY_SIZE_IN_BYTES = width * height / 8
'As the name implies, the number of bytes in the display portion of the RAM.'

WORDS_IN_SCANLINE = width / 32
'The number of 32-bit words in one horizontal scna line of the display.'


def screen_size_hack(ram, width=1024, height=768):
  '''
  Tuck a "magic number" and the screen dimensions into a location in RAM
  at the start of the display.  (I forget how they are used by the system.)
  If you have PyGame installed you can see the data in the pixels in the
  lower-left (origin) corner of the screen.
  '''
  ram[DISPLAY_START] = 0x53697A66  # magic value 'SIZE'+1
  ram[DISPLAY_START + 4] = width
  ram[DISPLAY_START + 8] = height


def coords_of_word(address):
  '''
  Given the address in words already adjusted for :py:obj:`DISPLAY_START` return
  a generator that yields the (x, y) coords of the pixels in that word.
  '''
  y, word_x = divmod(address, WORDS_IN_SCANLINE)
  y = height - y - 1
  pixel_x = word_x * 32
  for x in range(pixel_x, pixel_x + 32):
    yield x, y


def bits_of_int(i):
  '''Yield thirty-two bits, LSB to MSB, of an integer.'''
  for _ in range(32):
    yield i & 1
    i >>= 1


def update_screen(screen, address, value):
  '''
  Update the contents of the PyGame ``screen`` at ``address`` with the
  bit values from the integer ``value``.
  '''
  for coords, bit in zip(coords_of_word(address), bits_of_int(value)):
    screen.set_at(coords, 0xff * (1 - bit))
  display_flip()
