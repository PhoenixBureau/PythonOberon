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
from argparse import ArgumentParser, FileType
from pkg_resources import resource_filename
from sys import stderr
from traceback import print_exc
from .bootloader import bootloader
from .display import initialize_screen, ScreenRAMMixin
from .risc import (
    ByteAddressed32BitRAM,
    Clock,
    Disk,
    FakeSPI,
    LEDs,
    MemWords,
    Mouse,
    RISC,
    Serial,
    )
try:
    import pygame
except ImportError:
    pump = lambda: None
else:
    pump = pygame.event.pump


def make_arg_parser():
    '''
    Return an :py:class:`ArgumentParser` object.
    '''
    parser = ArgumentParser(
        prog='PythonOberon',
        usage='python -i -m oberon [-d DISK_IMAGE]',
        description='An emulator for Prof Wirth\'s RISC CPU for Project Oberon.',
        )
    parser.add_argument(
        '-d', '--disk-image',
        type=FileType('rb'),
        default=resource_filename(__name__, 'disk.img'),
        )
    parser.add_argument(
        '--serial-in',
        type=FileType('rb'),
        )
    return parser


def make_cpu(disk_image, serial=None):
    '''
    Build and return a :py:class:`RISC` object with peripherals.
    '''
    ram = Memory()
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
    risc_cpu.io_ports[24] = mouse = Mouse()
    mouse.set_coords(450, 474)
    fakespi.register(1, disk)
    return risc_cpu


class Memory(ScreenRAMMixin, ByteAddressed32BitRAM):
    '''RAM with memory-mapped raster display.'''


def cycle(cpu, limit):
    '''
    Run the ``cpu`` up to ``limit`` cycles.

    Flip the display (if any) every 10000 cycles.
    '''
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
