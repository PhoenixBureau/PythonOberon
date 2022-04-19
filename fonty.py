from bdflib import reader
from array import array
from string import printable
from struct import pack


DATA = array('I')

fn = './docs/extras/fornt/8x13.bdf'
with open(fn, 'rb') as f:
    font = reader.read_bdf(f)

for ch in printable[:-5]:
    DATA.extend(reversed(font[ord(ch)].data))

print(len(DATA), len(DATA) / 13)

binary = pack(f'>{len(DATA)}I', *DATA)

with open('8x13.bin', 'wb') as f:
    f.write(binary)

##a = font[ord('a')]
##print (a)
##for n in reversed(a.data):
##    b = bin(n)[2:]
##    pad = '0' * (8 - len(b))
##    print(f'{pad}{b}')
##    DATA.append(n)

