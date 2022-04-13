from random import randrange
from oberon.disassembler import dis

while True:
    print(dis(randrange(0, 2**32 - 1)))
