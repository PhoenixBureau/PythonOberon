from time import time


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
