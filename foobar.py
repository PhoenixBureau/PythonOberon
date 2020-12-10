import struct
import oberon.disassembler

with open('joy_asm.bin', 'rb') as f:
    data = f.read()

size_words = len(data) //  4
fmt = '<%ii' % size_words
machine_code = struct.unpack(fmt, data)

print len(data), divmod(len(data), 4)
for n in machine_code:
    print oberon.disassembler.dis(n)