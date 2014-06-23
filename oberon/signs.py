

def py2signed(i, width=32):
  assert width > 0
  width -= 1
  b = 2**width
  if not (-b <= i < b):
    raise ValueError
  if i >= 0:
    return i
  return b + i + (1 << width)


def signed2py(i, width=32):
  assert width > 0
  b = 2**width
  if not (0 <= i < b):
    raise ValueError
  if i < b / 2:
    return i
  return i - b
  

if __name__ == '__main__':
  W = 4
  for i in range(-10, 10):
    print '%2i' % i,
    try: s = py2signed(i, W)
    except ValueError: print
    else: print '  ->  %04s aka %i  ->  %2i' % (
      bin(s)[2:], s, signed2py(s, W)
      )
