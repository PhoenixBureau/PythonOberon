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
from pkg_resources import resource_filename
from io import BytesIO
from oberon.bootloader import bootloader
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


DISKIMG = resource_filename(__name__, '../disk.img')
FILLSCR = resource_filename(__name__, '../../FILLED.bin')
FILLSCR = resource_filename(__name__, '../../oberonforth.bin')
#FILLSCR = resource_filename(__name__, '../../fillscreen.bin')
#FILLSCR = resource_filename(__name__, '../../joy_asmii.bin')


def make_cpu(disk_image, serial=None):
    '''
    Build and return a :py:class:`RISC` object with peripherals.
    '''
    ram = ByteAddressed32BitRAM()
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


def strfi(fn):
    # Files can't be pickled, but BytesIO objects can.
    with open(fn, 'rb') as file_obj:
        return BytesIO(file_obj.read())


def newcpu(disk_filename=DISKIMG, serial_input_filename=FILLSCR):
    cpu = make_cpu(
        strfi(disk_filename),
        strfi(serial_input_filename),
        )
    cpu.breakpoints = 'PC == 0'
    cpu.watches = ''
    cpu.decode(0)  # Ensure that all attributes of the cpu have been created.
    return cpu


if __name__ == '__main__':
    import pickle
    cpu = newcpu()
    for _ in range(100):
        cpu.cycle()
    with open('default+100.pickle', 'wb') as f:
        pickle.dump(cpu, f)
