from oberon.assembler import Assembler
from oberon.disassembler import dis
from pprint import pformat

fn = '/usr/home/sforman/src/PythonOberon/oberonforth.py'
asm = compile(open(fn).read(), fn, 'exec')
# https://stackoverflow.com/questions/436198/what-is-an-alternative-to-execfile-in-python-3

a = Assembler()
p = a(asm)
##print(pformat(p))
#print 'a.here:', a.here
print()
a.print_program()

##program = []
##for addr in range(0, max(p)+4, 4):
##    if addr not in p:
##        print(f'0x{addr:04x} 0x00000000')
##        continue
##    i = p[addr]
##    if addr in a.data_addrs:
##        print(f'0x{addr:04x} 0x{i:08x}')
##        continue
##    print(f'0x{addr:04x} {dis(i)}')

##    b = f'{bin(i)[2:]:0>32}'
#    print(f'ram[0x00{hex(addr)[2:]:0>2}] = 0b_{b[:4]}_{b[4:8]}_{b[8:12]}_{b[12:16]}_{b[16:32]} # {e}')
#    print(f'ram[0x00{hex(addr)[2:]:0>2}] = 0b_{b[:4]}_{b[4:8]}_{b[8:12]}_{b[12:16]}_{b[16:28]}_{b[28:32]} # {e}')
##    print(f'ram[0x00{hex(addr)[2:]:0>2}] = 0b_{b[:8]}_{b[8:16]}_{b[16:24]}_{b[24:32]} # {e} - {f}')
    #print(f'{e}\n{f}\n')
#    print(f'0x00{hex(addr)[2:]:0>2}, {bin(i)[2:]:0>32}, {e}')
#    print(hex(addr), bin(i), e)
#  print hex(addr), (p[addr])

##
##f0  = 0b_00000000_00000000_00000000_00000000
##f1  = 0b_01000000_00000000_00000000_00000000
##f2  = 0b_10000000_00000000_00000000_00000000
##f3a = 0b_11000000_00000000_00000000_00000000
##f3b = 0b_11100000_00000000_00000000_00000000
##
##foramts = {
##  
##  }
##
##
##foramts[n>>29]
##



















