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
    print('Unable to import pygame.', file=stderr)
    PYGAME = False
else:
    PYGAME = True
    display_flip = pygame.display.flip

    WHITE = pygame.Color(0xFF, 0xFF, 0xFF)
    CURSOR = None



SIZE = WIDTH, HEIGHT = 1024, 768
'Size of the screen in pixels.'

DISPLAY_START = 0xE7F00
'RAM address of the start of the memory-mapped raster display.'

DISPLAY_SIZE_IN_BYTES = WIDTH * HEIGHT // 8
'As the name implies, the number of bytes in the display portion of the RAM.'

WORDS_IN_SCANLINE = WIDTH // 32
'The number of 32-bit words in one horizontal scan line of the display.'


WHITE = 23


def initialize_screen():
    '''
    Fire up PyGame and return a screen surface of :py:obj:`SIZE`.
    '''
    pygame.init()
    screen = pygame.display.set_mode(SIZE)
    global CURSOR
    CURSOR = pygame.Surface((32, 1), depth=screen.get_bitsize())
    return screen


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
        if (
            DISPLAY_START
            <= address
            < DISPLAY_START + DISPLAY_SIZE_IN_BYTES
        ):
            # Convert byte RAM address to word screen address.
            address = (address - DISPLAY_START) >> 2
            update_screen(self.screen, address, word)

    def __setitem__(self, key, value):
        self.put(key, value)


def screen_size_hack(ram, width=WIDTH, height=HEIGHT):
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
    y = HEIGHT - y - 1
    pixel_x = word_x * 32
    for x in range(pixel_x, pixel_x + 32):
        yield x, y


def bits_of_int(i):
    '''Yield thirty-two bits of an integer as 0 or 1, LSB to MSB.'''
    for _ in range(32):
        yield i & 1
        i >>= 1


def update_screen(screen, address, value):
    '''
    Update the contents of the PyGame ``screen`` at ``address`` with the
    bit values from the integer ``value``.
    '''
    COLORS = 0, (255, 255, 255)
    for x, bit in enumerate(bits_of_int(value)):
        CURSOR.set_at((x, 0), COLORS[bit])
    y, x = divmod(address, WORDS_IN_SCANLINE)
    screen.blit(CURSOR, (x << 5, HEIGHT - y - 1))
    display_flip()
