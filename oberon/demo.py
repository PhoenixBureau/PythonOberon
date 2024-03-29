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

Demonstrate the Emulator
=========================================

This module show how to instantiate the :py:class:`RISC` class and run it
with the Oberon OS disk image and some virtual peripherals.

'''
from sys import stderr
from traceback import print_exc
from oberon.bootloader import bootloader
from oberon.display import PYGAME, initialize_screen, ScreenRAMMixin
from oberon.risc import (
    ByteAddressed32BitRAM,
    Clock,
    Disk,
    FakeSPI,
    LEDs,
    Mouse,
    RISC,
    Serial,
    )

if PYGAME:
    import pygame
    pump = pygame.event.pump
    class Memory(ScreenRAMMixin, ByteAddressed32BitRAM):
        '''RAM with memory-mapped raster display.'''
else:
    pump = lambda: None
    Memory = ByteAddressed32BitRAM


def make_cpu(disk_image, serial=None):
    '''
    Build and return a :py:class:`RISC` object with peripherals.
    '''
    ram = Memory()
    if PYGAME:
        ram.set_screen(initialize_screen())
    disk = Disk(disk_image)
    risc_cpu = RISC(bootloader, ram)
    risc_cpu.io_ports[0] = Clock()
    risc_cpu.io_ports[4] = switches = LEDs()
    if serial:
        switches.switches |= 1
        risc_cpu.io_ports[8] = serial_port = Serial(serial)
        risc_cpu.io_ports[12] = serial_port.status
    risc_cpu.io_ports[20] = fakespi = FakeSPI()
    risc_cpu.io_ports[16] = fakespi.data
    fakespi.register(1, disk)
    risc_cpu.io_ports[24] = mouse = Mouse()
    mouse.set_coords(450, 474)
    return risc_cpu


def cycle(cpu, limit):
    '''
    Run the ``cpu`` up to ``limit`` cycles.

    Flip the display (if any) every 10000 cycles.
    '''
    count = 0
    while count < limit:
        try:
            cpu.cycle()
        except:  # pylint: disable=bare-except
            print_exc()
            cpu.dump_ram()
            break

        if not count % 10000:
            pump()
            print(count, file=stderr)
        count += 1
