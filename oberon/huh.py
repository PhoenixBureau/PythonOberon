# https://ipython.readthedocs.io/en/stable/config/eventloops.html#integrating-with-a-new-event-loop-in-the-terminal

def inputhook(context):
    while not context.input_is_ready():
        pump()

IPython.terminal.pt_inputhooks.register('pygame', inputhook)

#  %gui pygame

SIZE = WIDTH, HEIGHT = 1024, 768
WHITE = 0xff, 0xff, 0xff


pygame.init()
screen = pygame.display.set_mode(SIZE)


EBGaramond_FILE = '/usr/local/share/fonts/TTF/EBGaramond-Regular.ttf'

import pygame.freetype
pygame.freetype.init()

EBG_font = pygame.freetype.Font(EBGaramond_FILE)
EBG_font.size = 12


r = EBG_font.render_to(screen, (30, 30), "Hello World!", fgcolor=WHITE)
