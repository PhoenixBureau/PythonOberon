from traceback import print_exc
from .risc import (
  RISC,
  Disk,
  clock,
  LEDs,
  FakeSPI,
  Mouse,
  ByteAddressed32BitRAM,
  )
from .bootloader import bootloader
from .display import initialize_screen, ScreenRAMMixin


class Memory(ScreenRAMMixin, ByteAddressed32BitRAM):
  pass


memory = Memory()
memory.set_screen(initialize_screen())

disk = Disk('disk.img')

risc_cpu = RISC(bootloader, memory)

risc_cpu.io_ports[0] = clock()
risc_cpu.io_ports[4] = LEDs()
#  risc_cpu.io_ports[8] = RS232 data
#  risc_cpu.io_ports[12] = RS232 status
risc_cpu.io_ports[20] = fakespi = FakeSPI()
risc_cpu.io_ports[16] = fakespi.data
risc_cpu.io_ports[24] = mouse = Mouse()

mouse.set_coords(450, 474) # Imitate values in C trace.

fakespi.register(1, disk)


def cycle():
  while True:
    try:
      risc_cpu.cycle()
    except:
      print_exc()
      risc_cpu.dump_ram()
      break


cycle()
