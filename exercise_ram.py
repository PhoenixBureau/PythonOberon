from risc import ByteAddressed32BitRAM


d = ByteAddressed32BitRAM()
for n, ch in enumerate("Hello world!"):
  d.put_byte(n, ch)
print d
print ''.join(chr(d.get_byte(n)) for n in range(12))
