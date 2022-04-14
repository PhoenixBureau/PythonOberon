print('# Start')

from oberon.display import DISPLAY_START

N = 24575


def HIGH(i):
  return (i >> 16) & 0xFFFF


def LOW(i):
  return i & 0xFFFF


def move_immediate_word_to_register(reg, word):
  Mov_imm(reg, HIGH(word), u=1)
  Ior_imm(reg, reg, LOW(word))


a = 0
b = 1
c = 2
D = DISPLAY_START + N * 4
pattern = 0x33333333

T_imm(main)
label(_reserved, reserves=36)
label(main)
move_immediate_word_to_register(a, pattern)
move_immediate_word_to_register(b, D)
Mov_imm(c, N + 1)
label(loop)
Store_word(a, b, 0)
Sub_imm(b, b, 4)
Sub_imm(c, c, 1)
NE_imm(loop)

label(HALT) ; T_imm(HALT)


#r0 = 0
#label(some_data, 40)
#Mov(r0, 4)
print('# End')
print()
##print(
##'''
##import struct
##data = struct.pack('I'*len(program), *program)
##with open('fillscreen.bin', 'w') as f:
##  f.write(data)
##
##with open('fillscreen.bin') as f:
##  data = f.read()
##binary = struct.unpack('I'*(len(data) / 4), data)
##
##
##'''
##)
