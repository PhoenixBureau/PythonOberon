'''
To test run with::
    
    ipython --gui=tk -i -m oberon.IDE -- -n


'''
from Tkinter import (
    Tk,
    Entry,
    Frame,
    LabelFrame,
    Label,
    StringVar,
    LEFT,
    E,
    W,
    )


class Fullscreen_Window(object):

    def __init__(self):
        self.tk = Tk()
        self.frame = Frame(self.tk)
        self.frame.pack()
        self.fullscreen = False
        self.tk.bind("<F11>", self.toggle_fullscreen)
        self.tk.bind("<Escape>", self.end_fullscreen)

        self.registers = LabelFrame(
            self.frame,
            text='Registers'
            )
        self.registers.pack()
        self.register_vars = [
            self._register(i, i // 8, i % 8)
            for i in xrange(16)
            ]

    def _register(self, register_number, column, row):
        regwidg = RegisterWidget(self.registers, register_number)
        regwidg.grid(column=column, row=row, sticky=W)
        return regwidg

    def toggle_fullscreen(self, event=None):
        self.fullscreen = not self.fullscreen
        self.tk.attributes("-fullscreen", self.fullscreen)
        return "break"

    def end_fullscreen(self, event=None):
        self.fullscreen = False
        self.tk.attributes("-fullscreen", False)
        return "break"


class RegisterWidget(Frame):
    '''Display one register.'''

    FORMATS = [
        '%08x',
        (lambda n: (lambda s: '%s:%s' % (s[:4], s[4:]))('%08x' % (n,))),
        (lambda n: (lambda s: '%s:%s:%s:%s' % (s[:2], s[2:4], s[4:6], s[6:]))('%08x' % (n,))),
        '%i',
        hex,
    ]
    '''\
    A list of format strings or callables that are used to convert
    register values to strings for display.
    '''

    def __init__(self, root, register_number):
        Frame.__init__(self, root)
        
        self.current_format = 0
        'Index into the ring buffer of format strings for register label.'

        self._value = 0
        # Cache the int value to enable refresh after changing format.
        
        self.value = StringVar(self)
        'The current text to display.'

        self.set(self._value)

        Label(
            self,
            anchor=E,
            text='%x:' % register_number,
            width=3,
            ).pack(side=LEFT)
        # Anonymous label for the register display label.

        self.label = Entry(self, textvariable=self.value, state="readonly")
        'Display the register value.'

        self.label.bind('<Button-3>', self.toggle_format)
        self.label.pack(side=LEFT)

    def set(self, value):
        '''Given an integer value set the string value of the label.'''

        self._value = value  # So we can use it in toggle_format.

        formatter = self.FORMATS[self.current_format]

        if isinstance(formatter, basestring):
            label = formatter % (value,)
        elif callable(formatter):
            label = formatter(value)
        else:
            raise TypeError('wtf')

        self.value.set(label)

    def toggle_format(self, event=None):
        '''Switch to the next formatter.'''
        self.current_format = (self.current_format + 1) % len(self.FORMATS)
        self.set(self._value)
