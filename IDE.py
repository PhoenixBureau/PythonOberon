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


def one(cpu):
    cpu.cycle()
    os.system('clear')
    image(cpu)


def run(cpu, cycles=10000):
    for n in range(cycles):
        if not n % 100:
            pump()
        one(cpu)
        time.sleep(.01)


# Use the fill screen binary.
ARGS = ['--serial-in', './fillscreen.bin']

args = make_arg_parser().parse_args(ARGS)
cpu = make_cpu(
    strfi(args.disk_image),
    strfi(args.serial_in),
    )

run(cpu, 100)

# Disconnect the screen.  Can't pickle it.
S, cpu.ram.screen = cpu.ram.screen, None

with open('a.pickle', 'wb') as f:
    pickle.dump(cpu, f)

print 'BLINK!'
time.sleep(.25)

with open('a.pickle', 'rb') as f:
    new_cpu = pickle.load(f)

# Connect the screen to the new cpu object.
new_cpu.ram.screen = S

# Let 'er rip!
run(new_cpu)
