from oberon.assembler import Assembler, assemble_file
from oberon.disassembler import dis
from pprint import pformat

fn = '/usr/home/sforman/src/PythonOberon/oberonforth.py'
ofn = '/usr/home/sforman/src/PythonOberon/oberonforth.bin'
pfn = '/usr/home/sforman/src/PythonOberon/oberonforth.symbols'
assemble_file(fn, ofn, pfn)

a = Assembler()
p = a(compile(open(fn).read(), fn, 'exec'))

##print(pformat(p))

print()
a.print_program()
