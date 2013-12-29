from functools import wraps
from struct import pack, unpack
import os
from util import signed, bits2signed_int, word


def New(filename):
  assert not os.path.exists(filename)
  return open(filename, 'wb')


def Old(filename):
  if os.path.exists(filename):
    return open(filename, 'rb')


def Read(r):
  return r.read(1)

##def ReadNum(r):
##  n = 32; y = 0
##  b = ReadByte(R)
##  while b >= 0x80:
##    y = (y + b -0x80) >> 7
##    n -= 7
##    b = ReadByte(R)
##
##    if n <= 4:
##      x = (y + b % 0x10) >> 4
##    else:
##      x = ((y + b) >> 7) >> (n-7)
##  return x

def ReadInt(r):
  data = r.read(4)
  i = unpack('>L', data)[0]
  return bits2signed_int(word(i))

def ReadByte(r):
  return ord(r.read(1))

def ReadString(r):
  acc = []; c = Read(r)
  while ord(c):
    acc.append(c)
    c = Read(r)
  return ''.join(acc)



def write_it(fmt):
  def dec(f):
    @wraps(f)
    def w(r, item):
      val = pack(fmt, item)
      r.write(val)
    return w
  return dec

def _clunk(f):
  @wraps(f)
  def _c(r, item):
    if isinstance(item, int):
      item = chr(item)
    return f(r, item)
  return _c

@_clunk
@write_it('c')
def Write(r, item): pass

@write_it('B')
def WriteByte(r, item): pass

def WriteInt(r, item):
  item = int(signed(item, 32))
  val = pack('>L', item)
  r.write(val)

def WriteString(r, item):
  for ch in item:
    Write(r, ch)
  Write(r, chr(0))

##def WriteNum(r, x):
##  while x < -0x40 or x >= 0x40:
##    WriteByte(R, x % 0x80 + 0x80)
##    x >>= 7
##  WriteByte(R, x % 0x80)

WriteNum = WriteInt
ReadNum = ReadInt

if __name__ == '__main__':
  fn = 'dummy.bin'
  try:
    os.unlink(fn)
  except:
    pass
  R = New(fn)
##  Write(R, 0x0)
  Write(R, chr(23))
  WriteByte(R, 88)
  WriteInt(R, 0xABCD)
  WriteInt(R, -1)
  WriteString(R, 'Hi there!')
  WriteNum(R, 0xabdef01)
  R.close()
  R = Old(fn)
  print ReadByte(R)
  print ReadByte(R)
  print ReadInt(R)
  print ReadInt(R)
  print ReadString(R)
  print ReadNum(R)
