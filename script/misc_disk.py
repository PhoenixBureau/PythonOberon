from struct import pack, unpack

ram0 = 0x e7 00 24 0c
ram0l = 0x 0c 24 00 e7




DISK_IMAGE = './oberon/disk.img'

with open(DISK_IMAGE, 'rb') as f:
    disk_image = f.read()

print(f'read {len(disk_image)} bytes ({len(disk_image)//4} words) from {DISK_IMAGE}')

MAGIC_NUMBER = 0x9B1EA38D
SECTOR_SIZE = 512
SECTOR_SIZE_WORDS = SECTOR_SIZE // 4
STRUCT_FORMAT = '<%iI' % SECTOR_SIZE_WORDS


def read_sector(n, di=disk_image):
    '''return a list of word ints'''
    n *= SECTOR_SIZE
    data = di[n:n+SECTOR_SIZE]
    return unpack(STRUCT_FORMAT, data)


def ascar(word):
    b = list(pack('>I', word)) # 0x9b1ea38d -> [155, 30, 163, 141]
    return ''.join(
        chr(n)
        if 0x20 <= n <= 0x7e
        else '.'
        for n in b
        )


I = read_sector(2)
print(I.index(ram0))
print (ram0 in I, ram0l in I)
    
##for i, word in enumerate(I):
##    print(f'{i:03} 0x{i:02x} {word:08x} {ascar(word)}')

print()
