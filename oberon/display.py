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
from sys import stderr
try:
  import pygame
  from pygame.locals import *

except ImportError:
  print >> stderr, 'Unable to import pygame.'


  class FakeScreen:
    def set_at(self, (x, y), color):
      pass
  #    print x, y, color


  def initialize_screen():
    return FakeScreen()


  def display_flip():
    pass


  class ScreenRAMMixin(object):
    def set_screen(self, screen):
      screen_size_hack(self)


else:


  def initialize_screen():
    pygame.init()
    return pygame.display.set_mode(size, 0, 8)


  def display_flip():
    pygame.display.flip()


  class ScreenRAMMixin(object):

    def set_screen(self, screen):
      self.screen = screen
      screen_size_hack(self)

    def put(self, address, word):
      super(ScreenRAMMixin, self).put(address, word)
      if DISPLAY_START <= address < DISPLAY_START + DISPLAY_SIZE_IN_BYTES:
        # Convert byte RAM address to word screen address.
        address = (address - DISPLAY_START) >> 2
        update_screen(self.screen, address, word)

    def __setitem__(self, key, value):
      self.put(key, value)


size = width, height = 1024, 768

DISPLAY_START = 0xe7f00
DISPLAY_SIZE_IN_BYTES = width * height / 8
WORDS_IN_SCANLINE = width / 32


def screen_size_hack(ram, width=1024, height=768):
  ram[DISPLAY_START] = 0x53697A66  # magic value 'SIZE'+1
  ram[DISPLAY_START + 4] = width
  ram[DISPLAY_START + 8] = height


def coords_of_word(address):
  '''
  Given the address in words already adjusted for DISPLAY_START return
  a generator that yields the (x, y) coords of the pixels in that word.
  '''
  y, word_x = divmod(address, WORDS_IN_SCANLINE)
  y = height - y - 1
  pixel_x = word_x * 32
  for x in range(pixel_x, pixel_x + 32):
    yield x, y


def bits_of_int(i):
  for _ in range(32):
    yield i & 1
    i >>= 1


def update_screen(screen, address, value):
  for coords, bit in zip(coords_of_word(address), bits_of_int(value)):
    screen.set_at(coords, 0xff * (1 - bit))
  display_flip()
