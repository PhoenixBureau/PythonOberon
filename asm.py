from oberon.assembler import Assembler
from oberon.disassembler import dis
from pprint import pformat

fn = '/usr/home/sforman/src/PythonOberon/oberonforth.py'
asm = compile(open(fn).read(), fn, 'exec')
a = Assembler()
p = a(asm)

##print(pformat(p))

print()
a.print_program()
