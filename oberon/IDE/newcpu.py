from pkg_resources import resource_filename
from StringIO import StringIO
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
FILLSCR = resource_filename(__name__, '../../fillscreen.bin')


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
    # Files can't be pickled, but StringIO objects can.
    with open(fn, 'rb') as file_obj:
        return StringIO(file_obj.read())


def newcpu():
    return make_cpu(strfi(DISKIMG), strfi(FILLSCR))


if __name__ == '__main__':
    import pickle
    cpu = newcpu()
    for _ in xrange(100):
        cpu.cycle()
    with open('default+100.pickle', 'wb') as f:
        pickle.dump(cpu, f)
