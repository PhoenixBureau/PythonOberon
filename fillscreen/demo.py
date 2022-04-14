from struct import unpack
from oberon.assembler import assemble_file
from oberon.disassembler import dis


assemble_file('fillscreen.py', 'FILLED.bin')


def foo(fn):
    with open(fn, 'rb') as f:
        data = f.read()
    j = unpack(f'<{len(data)//4}I', data)
    print(fn)
    for i, n in enumerate(j):
        print(f'    {i:-2} 0x{i*4:02x} 0x{n:08x} {dis(n)}')


foo('FILLED.bin')
print()
foo('fillscreen.bin')


##from oberon.display import DISPLAY_START
##binary = unpack('<'+'I'*(len(data)//4), data)
##
##'''
##Convert a signed Python int to a 32-bit C unsigned value.
##'''
##
####Mov_imm(0, 0x3333, v=False, u=True)
####Ior_imm(0, 0, 0x3333, v=False, u=False)
####Mov_imm(1, 0xf, v=False, u=True)
####Ior_imm(1, 1, 0xfefc, v=False, u=False)
####Mov_imm(2, 0x6000, v=False, u=False)
####Store_word(0, 1)
####Sub_imm(1, 1, 0x4, v=False, u=False)
####Sub_imm(2, 2, 0x1, v=False, u=False)
####NE_imm(-0x4)
####T_imm(-0x1)
##def u_to_s_16(g): return unpack('<h', pack('<H', g))[0]
##def s_to_u_16(g): return unpack('<H', pack('<h', g))[0]
##def u_to_s_32(g): return unpack('<i', pack('<I', g))[0]
##def s_to_u_32(g): return unpack('<I', pack('<i', g))[0]
##
##N = 24575
##D = DISPLAY_START + N * 4
##print(hex(D))
##assert D == 0xffefc
##
