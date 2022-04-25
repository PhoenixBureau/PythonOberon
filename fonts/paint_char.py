from bdflib import reader
from array import array
from itertools import *
##from string import printable
##from struct import pack

##>>> ''.join(map(chr, sorted(map(ord, printable[:-5]))))
##' !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~'

CHARS = (
    '!"#$%&\'()*+,-./'
    '0123456789'
    ':;<=>?@'
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    '[\\]^_`'
    'abcdefghijklmnopqrstuvwxyz'
    '{|}~'
    )

DATA = array('I')
with open('8x13.bintoo', 'rb') as f:
    DATA.frombytes(f.read())
DATA.pop(0)  # DISPLAY_START


def pixy(word, one='@', zero=' '):
    bits = bin(word)[2:]
    bits = '0' * max(0, 32 - len(bits)) + bits
    return bits .replace('0', zero).replace('1', one)


for i, n in enumerate(DATA):
##for i, n in enumerate(chain.from_iterable(js)):
    print(pixy(n))
    if 0 == (i % 13):
        print('-------|' * 4)


WORDS_IN_SCANLINE = 32

# At 1024px wide, and each char is 8px wide, that gives
# 128 chars wide.  And 768px // 13px = 59 lines high.
# The formula to convert 0 <= x < 128 and 0 <= y <= 59
# to the address in video RAM is...

def foo(x, y, display_start):
    return (
        y * 128  # 128 == WORDS_IN_SCANLINE * 4
        + x * 8
        + display_start
        )

# But it's not quite that simple.  In Oberon the screen
# (0, 0) pixel is in the lower left corner, and Y increases
# as one goes UP the screen (not down as is typical and
# inexplicable in most screens.  It's not really inexplicable,
# it's that way because originally we were printing out on
# teletype machines, so it was natural in that context that
# Y (or the line number) increases as you go DOWN.)
# Mathematically it's much nicer to work in the x+, y+ quadrant.

def foo(x, y, display_start, display_height=768):
    assert 0 <= x < 128 and 0 <= y <= 59
    return (
        (display_height - y * 128 - 1)  # 128 == WORDS_IN_SCANLINE * 4
        + x * 8
        + display_start
        )



'''

Let's imagine that we want to draw a character in the upper left corner.
The first byte would go (768 - 1) lines up from display_start,
and each line is 1024 pixels, 128 bytes, or 32 words wide,
RAM is counted in bytes, so (768 - 1) * 128 = 98176 bytes from display_start
The x coord is already in bytes!  (Because our font is one byte wide.)

So we would start at display_start + 98176 and decrement by 128.


'''
DISPLAY_START = 0xE7F00
DISPLAY_LENGTH = 0x18000
R7 = 7

defcode(b'paint-chars', PAINT_CHARS)
move_immediate_word_to_register(R0, DISPLAY_START)
move_immediate_word_to_register(R1, DISPLAY_LENGTH)
Add_imm(R1, R1, R0)
Mov_imm(R2, 52)

label(_pchr_loop)  # <-------------
Load_word(R7, R0)
Store_word(R7, R1)
Add_imm(R0, R0, 4)
Sub_imm(R1, R1, 128)
Sub_imm(R2, R2, 1)
EQ_imm(_done)
T_imm(_pchr_loop)
label(_done)  # <-------------
NEXT()




####
##### R0 has the char to emit
####POP(R0)
####Mul_imm(R0, 52)  # 4 bytes/word * 13 words
####Add_imm(R0, R0, FONT)
####
##### R2 is set to point to first word of output
##### location in video ram.
####POP(R1)                         # x
####Lsl_imm(R1, 3)                  # x *= 8
####POP(R2)                         # y
####Lsl_imm(R2, R2, 7)              # y *= 128
####Add(R2, R2, R1)                 # y += x
####Add_imm(R2, R2, DISPLAY_START)  # y += display_start
####
####
##### Copy 13 words from font data to video RAM.
##### Unroll the loop.
####for i in range(0, 52, 4):
####    Load_word(R1, R0, i)
####    Store_word(R1, R2, i * WORDS_IN_SCANLINE)
####
####
####
####
####
####
####
######'''
######DISPLAY_START = 0xE7F00
######
######defcode(b'paint-chars', PAINT_CHARS)
######
####### R0 has the char to emit
######POP(R0)
######Mul_imm(R0, 52)  # 4 bytes/word * 13 words
######Add_imm(R0, R0, FONT)
######
####### R2 is set to point to first word of output
####### location in video ram.
######POP(R1)                         # x
######Lsl_imm(R1, 3)                  # x *= 8
######POP(R2)                         # y
######Lsl_imm(R2, R2, 7)              # y *= 128
######Add(R2, R2, R1)                 # y += x
######Add_imm(R2, R2, DISPLAY_START)  # y += display_start
######
######
####### Copy 13 words from font data to video RAM.
####### Unroll the loop.
######for i in range(0, 52, 4):
######    Load_word(R1, R0, i)
######    Store_word(R1, R2, i * WORDS_IN_SCANLINE)
