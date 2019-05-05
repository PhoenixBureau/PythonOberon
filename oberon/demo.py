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
from .risc import (
    ByteAddressed32BitRAM,
    clock,
    Disk,
    FakeSPI,
    LEDs,
    MemWords,
    Mouse,
    RISC,
    )
from .bootloader import bootloader
from .display import initialize_screen, ScreenRAMMixin


class Memory(ScreenRAMMixin, ByteAddressed32BitRAM):
    pass


def make_cpu(bootloader, ram, disk):
    risc_cpu = RISC(bootloader, ram)
    risc_cpu.io_ports[0] = clock()
    risc_cpu.io_ports[4] = LEDs()
    #  risc_cpu.io_ports[8] = RS232 data
    #  risc_cpu.io_ports[12] = RS232 status
    risc_cpu.io_ports[20] = fakespi = FakeSPI()
    risc_cpu.io_ports[16] = fakespi.data
    risc_cpu.io_ports[24] = Mouse()
    fakespi.register(1, disk)
    return risc_cpu


# ram = Memory()
# ram.set_screen(initialize_screen())
# disk = Disk('disk.img')
# cpu = make_cpu(bootloader, ram, disk)
