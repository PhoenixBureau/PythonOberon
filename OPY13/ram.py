

F = 2**32-1


class ByteAddressed32BitRAM(object):

  def __init__(self):
    self.store = {}

  def get(self, addr):
    word_addr, byte_offset = divmod(addr, 4)
    assert not byte_offset, repr(addr)
    return self.store[word_addr]

  __getitem__ = get

  def put(self, addr, word):
    assert 0 <= word < 2**32, repr(word)
    word_addr, byte_offset = divmod(addr, 4)
    assert not byte_offset, repr(addr)
    self.store[word_addr] = word

  __setitem__ = put

  def get_byte(self, addr):
    word_addr, byte_offset = divmod(addr, 4)
    word = self.store[word_addr]
    return (word >> (8 * byte_offset)) & 255

  def put_byte(self, addr, byte):
    assert 0 <= byte < 256, repr(byte)
    word_addr, byte_offset = divmod(addr, 4)
    n = 8 * byte_offset
    byte <<= n
    if word_addr not in self.store:
      self.store[word_addr] = byte
    else:
      mask = F ^ (255 << n)
      word = self.store[word_addr]
      self.store[word_addr] = word & mask | byte

  def __len__(self):
    return 4 * max(self.store or [0])

  def __repr__(self):
    import pprint
    return pprint.pformat(self.store)


if __name__ == '__main__':
  d = ByteAddressed32BitRAM()
  for n, ch in enumerate("Hello world!"):
    d.put_byte(n, ord(ch))
  print d
  print ''.join(chr(d.get_byte(n)) for n in range(12))
