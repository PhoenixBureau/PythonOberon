from array import array
from pathlib import Path
from oberon.disassembler import dis


dump = Path('/usr/home/sforman/src/PythonOberon/forth/dump')
DATA = array('I')
with dump.open(mode='rb') as f:
    DATA.fromfile(f, dump.stat().st_size // DATA.itemsize)
for i, instr in enumerate(DATA):
    print(f'{i<<2:05x} 0x{instr:08x} {dis(instr)}')
