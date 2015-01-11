from sys import stderr
from time import time
from collections import defaultdict
import pdb
from struct import unpack


diskCommand, diskRead, diskWrite, diskWriting = 0, 1, 2, 3


def log(message, *args):
  pass
##  print message % args
##  print >> stderr, message % args


class Disk(object):

  SECTOR_SIZE = 512
  SECTOR_SIZE_WORDS = SECTOR_SIZE / 4

  def __init__(self, filename='disk.img'):
    self.state = diskCommand

    self.rx_buf = [None] * self.SECTOR_SIZE_WORDS
    self.rx_idx = 0

    self.tx_buf = [None] * (self.SECTOR_SIZE_WORDS + 2)
    self.tx_cnt = 0
    self.tx_idx = 0

    self.file = open(filename, 'rb')
    self.read_sector()
    self.offset = 0x80002 if self.tx_buf[0] == 0x9B1EA38D else 0

  def read(self):
    if self.tx_idx >= 0 and self.tx_idx < self.tx_cnt:
      log('disk_read from buffer 0x%x', self.tx_buf[self.tx_idx])
      return self.tx_buf[self.tx_idx]
    log('disk_read from default 0xFF')
    return 255

  def write(self, word):
    log('disk_write 0x%x', word)

    self.tx_idx += 1

    if self.state == diskCommand:
      if (0xff & word) == 0xff and self.rx_idx == 0:
        log('disk_write PASS 0x%x', word)
        return
      log('disk_write diskCommand 0x%x to rx_buf[%i]', word, self.rx_idx)
      self.rx_buf[self.rx_idx] = word
      self.rx_idx += 1
      if self.rx_idx == 6:
##        pdb.set_trace()
        self.run_command()
        self.rx_idx = 0

    elif self.state == diskRead:
      if self.tx_idx == self.tx_cnt:
        self.state = diskCommand
        log('disk_write diskRead -> diskCommand')
        self.tx_cnt = 0
        self.tx_idx = 0

    elif self.state == diskWrite:
      if word == 254:
        self.state = diskWriting
        log('disk_write diskWrite -> diskWriting')

    elif self.state == diskWriting:
      if self.rx_idx < 128:
        self.rx_buf[self.rx_idx] = word

      self.rx_idx += 1

      if self.rx_idx == 128:
        self.write_sector()

      if self.rx_idx == 130:
        self.tx_buf[0] = 5
        self.tx_cnt = 1
        self.tx_idx = -1
        self.rx_idx = 0
        self.state = diskCommand
        log('disk_write diskWriting -> diskCommand')

  def run_command(self):
    cmd, a, b, c, d = self.rx_buf[0:5]
    a, b, c, d = (n & 0xff for n in (a, b, c, d))
    arg = (a << 24) | (b << 16) | (c << 8) | d
    log('run_command ' + ' '.join(map(hex, (cmd, arg))))

    if cmd == 81:
      self.state = diskRead
      self.tx_buf[0] = 0
      self.tx_buf[1] = 254
      self._seek(arg)
##      pdb.set_trace()
      self.read_sector(2)
      self.tx_cnt = 2 + 128

    elif cmd == 88:
      self.state = diskWrite
      self._seek(arg)
      self.tx_buf[0] = 0
      self.tx_cnt = 1

    else:
      self.tx_buf[0] = 0
      self.tx_cnt = 1

    self.tx_idx = -1

  def _seek(self, arg):
    log('#' * 100)
    a = (arg - self.offset) * self.SECTOR_SIZE
    log('seeking to %i (0x%x)', arg, a)
    self.file.seek(a)
      
  def read_sector(self, into=0):
    data = self.file.read(self.SECTOR_SIZE)
    self.tx_buf[into:] = unpack('<128I', data)

  def write_sector(self):
    log('write sector %r', self.rx_buf)
#    data = pack('<128I', self.rx_buf)
#    self.file.write(data)


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
    print 'LEDs', bin(word)[2:]


class FakeSPI(object):

  def __init__(self):
    self.things = {}
    self.current_thing = None

    class DataControl(object):

      def read(inner):
        if self.current_thing:
          data = self.current_thing.read()
        else:
          data = 0xff
        log('FakeSPI Data Read: 0x%x', data)
        return data

      def write(inner, word):
        log('FakeSPI Data Write: 0x%x', word)
        if self.current_thing:
          self.current_thing.write(word)

    self.data = DataControl()

  def register(self, index, thing):
    self.things[index] = thing

  def read(self):
    log('FakeSPI Control Read: 0x1')
    return 1

  def write(self, word):
    log('FakeSPI Control Write: 0x%x', word)
    word %= 4
    try:
      self.current_thing = self.things[word]
      log('Setting SPI device to %s', self.current_thing)
    except KeyError:
      log('No SPI device %i', word)
      self.current_thing = None


if __name__ == '__main__':
  disk = Disk()
  print disk.read_data()
