from sys import stderr
from time import time
from collections import defaultdict


dmiRead = 0
dmiWrite = 1
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
      print >> stderr, 'disk', ('dmiRead', 'dmiWrite')[word]

    elif self.state == self.READ_SRC:
      self.src = word
      self.state = self.READ_DST
      print >> stderr, 'disk src <-', hex(word)

    else:
      assert self.state == self.READ_DST
      self.dst = word
      self.state = self.READ_COMMAND
      print >> stderr, 'disk dst <-', hex(word)

      if self.direction == dmiRead:
        self.read_block()
      else:
        self.write_block()

  def read_block(self):
    sector = self.data[self.src]
    ram_addrs = range(self.dst, self.dst + SectorLength, 4)
    print >> stderr, 'disk read_block RAM: 0x%x <- disk: 0x%x' % (self.dst, self.src)
    for addr, word in zip(ram_addrs, sector):
      self.ram[addr] = word

  def write_block(self):
    sector = map(
      self._ram_or_zero,
      xrange(self.src, self.src + SectorLength, 4)
      )
    self.data[self.dst] = sector
    print >> stderr, 'disk write_block disk: 0x%x <- RAM: 0x%x' % (self.dst, self.src)

  def _ram_or_zero(self, addr):
    try:
      return self.ram[addr]
    except KeyError:
      return 0

  def read(self):
    print >> stderr, 'disk read() RAM: 0x%x <- disk: 0x%x' % (self.dst, self.src)
    return 1
    raise NotImplementedError


def fake_sector():
  return [0xdeadbeef for n in xrange(0, SectorLength, 4)]


def fake_disk():
  return defaultdict(fake_sector)


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


class LEDs(object):

  def read(self):
    return 0

  def write(self, word):
    print >> stderr, 'LEDs', bin(word)[2:]


class FakeSPI(object):

  def read(self):
    print >> stderr, 'FakeSPI read'
    return 1

  def write(self, word):
    print >> stderr, 'FakeSPI write', bin(word)[2:]


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
