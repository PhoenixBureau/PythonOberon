'''
      $0 $1 ... $F
$00    .  .
$10
$20
...
$F0

'''
from string import printable

#print(repr(printable))
#print(len(printable))

P = set('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~')

def chro(n):
    ch = chr(n)
    return f'{ch}' if ch in P else f'{n:02X}'


print('   ', ' '.join(f'$0{n:X}' for n in range(16))) 

for row in range(0, 0x80, 0x10):
    print(f'${row:02X} ', '   '.join(chro(row + n) for n in range(16)))
