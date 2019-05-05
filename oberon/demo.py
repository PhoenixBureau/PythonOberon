from .risc import (
    RISC,
    Disk,
    clock,
    LEDs,
    FakeSPI,
    Mouse,
    ByteAddressed32BitRAM,
    MemWords,
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
