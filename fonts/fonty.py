from bdflib import reader
from array import array
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

fn = './docs/extras/fornt/8x13.bdf'
with open(fn, 'rb') as f:
    font = reader.read_bdf(f)

for codepoint in sorted(map(ord, CHARS)):
    DATA.extend(reversed(font[codepoint].data))

print(len(DATA), len(DATA) / 13)

##binary = pack(f'<{len(DATA)}I', *DATA)
##
##with open('8x13.bin', 'wb') as f:
##    f.write(binary)

with open('8x13.bintoo', 'wb') as f:
    DATA.tofile(f)


##a = font[ord('a')]
##print (a)
for i, n in enumerate(DATA):
    b = bin(n)[2:]
    pad = '0' * (8 - len(b))
    print(f'{pad}{b}'.replace('0', ' ').replace('1', '0'))
##    DATA.append(n)


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


defcode(b'paint-char', PAINT_CHAR)

# R0 has the char to emit
POP(R0)
Mul_imm(R0, 52)  # 4 bytes/word * 13 words
Add_imm(R0, R0, FONT)

# R2 is set to point to first word of output
# location in video ram.
POP(R1)                         # x
Lsl_imm(R1, 3)                  # x *= 8
POP(R2)                         # y
Lsl_imm(R2, R2, 7)              # y *= 128
Add(R2, R2, R1)                 # y += x
Add_imm(R2, R2, DISPLAY_START)  # y += display_start


# Copy 13 words from font data to video RAM.
# Unroll the loop.
for i in range(0, 52, 4):
    Load_word(R1, R0, i)
    Store_word(R1, R2, i * WORDS_IN_SCANLINE)
