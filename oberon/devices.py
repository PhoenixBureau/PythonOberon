from time import time


dmiRead = 0; dmiWrite = 1;
SectorLength = 1024


class BlockDeviceWithDMI(object):

  READ_COMMAND = 0
  READ_SRC = 1
  READ_DST = 2

  def __init__(self, ram, data=None):
    self.ram = ram
    if data is None:
      data = {}
    self.data = data
    self.state = self.READ_COMMAND
    self.direction = dmiRead
    self.src = self.dst = 0

  def write(self, word):
    if self.state == self.READ_COMMAND:
      assert word in {dmiRead, dmiWrite}, repr(word)
      self.direction = word
      self.state = self.READ_SRC

    elif self.state == self.READ_SRC:
      self.src = word
      self.state = self.READ_DST

    else:
      assert self.state == self.READ_DST
      self.dst = word
      self.state = self.READ_COMMAND

      if self.direction == dmiRead:
        self.read_block()
      else:
        self.write_block()

  def read_block(self):
    sector = self.data[self.src]
    ram_addrs = range(self.dst, self.dst + SectorLength, 4)
    for addr, word in zip(ram_addrs, sector):
      self.ram[addr] = word

  def write_block(self):
    sector = map(
      self._ram_or_zero,
      xrange(self.src, self.src + SectorLength, 4)
      )
    self.data[self.dst] = sector

  def _ram_or_zero(self, addr):
    try:
      return self.ram[addr]
    except KeyError:
      return 0

  def read(self):
    raise NotImplementedError


class clock(object):

  def __init__(self, now=None):
    self.reset(now)

  def read(self):
    return self.time() - self.start_time

  def write(self, word): # RESERVED
    raise NotImplementedError

  def reset(self, now=None):
    self.start_time = now or self.time()

  def time(self):
    '''Return int time in ms.'''
    return int(round(1000 * time()))


if __name__ == '__main__':
  from pprint import pprint
  from ram import ByteAddressed32BitRAM
  d = ByteAddressed32BitRAM()
  for n, ch in enumerate("Hello world!"):
    d.put_byte(n, ord(ch))
  b = BlockDeviceWithDMI(d)
  pprint(b.data)
  b.write(dmiWrite)
  b.write(0)
  b.write(0)
  pprint(b.data)
