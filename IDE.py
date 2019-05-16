import os, pickle, StringIO, time
from oberon.assembler import dis
from oberon.demo import make_arg_parser, make_cpu
from oberon.demo import pump, cycle


def image(cpu):
    kw = cpu.__dict__.copy()
    print '=' * 36
    print 'PC: 0x%(PC)08x:' % kw, dis(int(cpu.IR))
    print '-' * 36
    for ia, ra, ib, rb in zip(
        range(8),     cpu.R[0:8],
        range(8, 16), cpu.R[8:16]
        ):
        print 'r%i: 0x%08x  ::  r%02i: 0x%08x' % (ia, ra, ib, rb)
    print '-' * 36
    print 'H: 0x%(H)08x N:%(N)i Z:%(Z)i C:%(C)i OV:%(OV)i' % kw
    print '=' * 36


def strfi(file_obj):
    return StringIO.StringIO(file_obj.read())


def disconnect(cpu):
    # disk = cpu.io_ports[20].things[1]
    # serial_port = cpu.io_ports[8]
    # D, disk.file = disk.file, None
    S, cpu.ram.screen = cpu.ram.screen, None
    # F, serial_port.input_file = serial_port.input_file, None
    return S


args = make_arg_parser().parse_args(['--serial-in', './fillscreen.bin'])
cpu = make_cpu(
    strfi(args.disk_image),
    strfi(args.serial_in),
    )
print


def one():
    cpu.cycle()
    os.system('clear')
    image(cpu)


for n in range(100):
    if not n % 100: pump()
    one()
    time.sleep(.01)

unpicklable = disconnect(cpu)
with open('a.pickle', 'wb') as f:
    pickle.dump(cpu, f)
