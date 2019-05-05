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
from argparse import ArgumentParser, FileType
from sys import stderr
from traceback import print_exc
from .bootloader import bootloader
from .demo import Memory, make_cpu
from .display import initialize_screen
from .risc import Disk
try:
  import pygame
except ImportError:
  pump = lambda: None
else:
  pump = pygame.event.pump


parser = ArgumentParser(
  prog='PythonOberon',
  usage='python -i -m oberon [-d DISK_IMAGE]',
  description='An emulator for Prof Wirth\'s RISC CPU for Project Oberon.',
  )
parser.add_argument(
  '-d', '--disk-image',
  type=FileType('rb'),
  default='disk.img',
  )
args = parser.parse_args()

print 'Using disk image file', args.disk_image.name

memory = Memory()
memory.set_screen(initialize_screen())
disk = Disk(args.disk_image)
cpu = make_cpu(bootloader, memory, disk)
mouse = cpu.io_ports[24]
mouse.set_coords(450, 474) # Imitate values in C trace.


def cycle(cpu, limit):
  n = 0
  while n < limit:
    try:
      cpu.cycle()
    except:
      print_exc()
      cpu.dump_ram()
      break

    if not n % 10000:
      pump()
      print >> stderr, n
    n += 1


# Details begin to be painted around 6.5M cycles.
cycle(cpu, 8000000)
