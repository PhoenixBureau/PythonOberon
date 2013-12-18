
import os, pickle


def New(filename):
  assert not os.path.exists(filename)
  return open(filename, 'wb')


def Old(filename):
  if os.path.exists(filename):
    return open(filename, 'rb')


def ReadNum(r):
  item = pickle.load(r)
  return item
ReadString = ReadByte = ReadInt = ReadNum


def WriteNum(r, item):
  pickle.dump(item, r)
WriteString = WriteByte = WriteInt = WriteNum


if __name__ == '__main__':
  fn = 'dummy.pickle'
  R = New(fn)
  WriteNum(R, 23)
  R = Old(fn)
  print ReadNum(R)
  os.unlink(fn)
