from oberon.bootloader import bootloader
from oberon.disassembler import dis
from oberon.risc import ROMStart

for i, instruction in enumerate(bootloader):
    print('0x%08x - 0x%04x : %s' % (i + ROMStart, i, dis(instruction)))
