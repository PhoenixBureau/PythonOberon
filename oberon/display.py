from sys import stderr
import pygame
from pygame.locals import *


size = width, height = 1024, 768

DISPLAY_START = 0xe7f00
DISPLAY_SIZE_IN_BYTES = width * height / 8
DISPLAY_SIZE_IN_WORDS = width * height / 32

words_in_horizontal_scanline = width / 32


def coords_of_word(address):
  '''
  Given the address in words already adjusted for DISPLAY_START return
  a generator that yields the (x, y) coords of the pixels in that word.
  '''
  y, word_x = divmod(address, words_in_horizontal_scanline)
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
  pygame.display.flip()


class ScreenRAMMixin(object):

  def set_screen(self, screen):
    self.screen = screen

  def put(self, address, word):
    super(ScreenRAMMixin, self).put(address, word)
    if DISPLAY_START <= address < DISPLAY_START + DISPLAY_SIZE_IN_BYTES:
      print >> stderr, 'updating display ram 0x%08x: %s' % (address, bin(word)[2:])
      # Convert byte RAM address to word screen address.
      address = (address - DISPLAY_START) >> 2
      update_screen(self.screen, address, word)

  def __setitem__(self, key, value):
    self.put(key, value)


if __name__ == '__main__':
  from traceback import print_exc
  from risc import ByteAddressed32BitRAM, RISC
  from devices import LEDs, FakeSPI, Disk, clock, Mouse
  from bootloader import bootloader

  pygame.init()
  screen = pygame.display.set_mode(size, 0, 8)

  class Memory(ScreenRAMMixin, ByteAddressed32BitRAM):
    pass

  memory = Memory()
  memory.set_screen(screen)

  disk = Disk('disk.img')

  risc_cpu = RISC(bootloader, memory)
  risc_cpu.screen_size_hack()

  risc_cpu.io_ports[0] = clock()
  risc_cpu.io_ports[4] = LEDs()
  risc_cpu.io_ports[20] = fakespi = FakeSPI()
  risc_cpu.io_ports[16] = fakespi.data
  risc_cpu.io_ports[24] = mouse = Mouse()

  mouse.set_coords(450, 474) # Imitate values in C trace.

  fakespi.register(1, disk)

  n = 0
  while n < 8000000:
    n += 1
    if not n % 1000:
      print n

    try:
      risc_cpu.cycle()
    except:
      print_exc()
      risc_cpu.dump_ram()
      break
