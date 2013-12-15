import oberon


def run_tests():
  reload(oberon)
  for inp in oberon.test_strings:
    print repr(inp), '->', repr(oberon.OberonParser.match(inp))


if __name__ == '__main__':
  run_tests()
