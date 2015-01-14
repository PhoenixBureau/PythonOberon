import pygame
from pygame.locals import *
from util import bint


size = width, height = 1024, 768

DISPLAY_START = 0xe7f00
DISPLAY_SIZE = width * height / 32

words_in_horizontal_scanline = width / 32


def iter_coords_of_word(address):
  word_x, word_y = divmod(address, words_in_horizontal_scanline)
  pixel_y = word_y * 32
  for y in range(pixel_y, pixel_y + 32):
    yield word_x, y


def update_screen(screen, address, value):
  value = bint(value)
  bits = (value[i] for i in range(32))
  coords = iter_coords_of_word(address)
  for (x, y), bit in zip(coords, bits):
    screen.set_at((x, y), 0xff * bit)


def wrap_memory(mem, screen):
  mem_put = mem.put

  def put(self, address, word):
    mem_put(address, word)
    if DISPLAY_START <= address < DISPLAY_START + DISPLAY_SIZE:
      print 'updating display ram 0x%08x: %s' % (address, bin(word)[2:])
      address = (address - DISPLAY_START) << 2
      update_screen(screen, address, word)
      pygame.display.flip()

  mem.put = put
  return mem


if __name__ == '__main__':
  from risc import ByteAddressed32BitRAM, RISC
  from devices import LEDs, FakeSPI, Disk
  from bootloader import bootloader

  pygame.init()
  screen = pygame.display.set_mode(size, 0, 8)

  memory = wrap_memory(ByteAddressed32BitRAM(), screen)

  disk = Disk('disk.img')

  risc_cpu = RISC(bootloader, memory)

  risc_cpu.io_ports[4] = LEDs()
  risc_cpu.io_ports[20] = fakespi = FakeSPI()
  risc_cpu.io_ports[16] = fakespi.data

  fakespi.register(1, disk)

  while True:

    try:
      risc_cpu.cycle()
    except:
      risc_cpu.dump_ram()
      break
