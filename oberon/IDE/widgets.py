'''
To test run with::
    
    ipython --gui=tk -i -m oberon.IDE -- -n


'''
from Tkinter import (
    Tk,

    Checkbutton,
    Entry,
    Frame,
    IntVar,
    Label,
    LabelFrame,
    StringVar,

    E,
    LEFT,
    W,
    )
import tkFont


class DebugApp(object):

    def __init__(self):
        self.tk = Tk()
        self.font = tkFont.Font(family='Courier', size=8)
        self.frame = Frame(self.tk)
        self.frame.pack()

        self.register_frame = LabelFrame(self.frame, text='Registers')
        self.register_frame.pack()

        self.register_widgets = [
            self._register(self.register_frame, '%x:' % i, i // 8, i % 8)
            for i in xrange(16)
            ]

        self.specials = LabelFrame(self.frame, text='Specials')
        self.specials.pack()

        self.PC = self._register(self.specials, 'PC:')
        self.H = self._register(self.specials, 'H:', row=1)

        self.N = self._flag(self.specials, 'N:', column=1)
        self.Z = self._flag(self.specials, 'Z:', column=2)
        self.C = self._flag(self.specials, 'C:', column=1, row=1)
        self.OV = self._flag(self.specials, 'OV:', column=2, row=1)

    def _register(self, frame, register_number, column=0, row=0):
        regwidg = RegisterWidget(frame, register_number, self.font)
        regwidg.grid(column=column, row=row, sticky=W)
        return regwidg

    def _flag(self, frame, label, column=0, row=0):
        flagwidg = FlagWidget(frame, label, self.font)
        flagwidg.grid(column=column, row=row, sticky=W)
        return flagwidg


class FlagWidget(Frame):
    '''Display a binary Boolean flag.'''

    def __init__(self, root, label_text, font):
        Frame.__init__(self, root)
        
        Label(  # I want the label on the left, Checkbox widget built-in labels are on the right only.
            self,
            anchor=E,
            font=font,
            text=label_text,
            width=3,
            ).pack(side=LEFT)

        self.value = IntVar(self, value=0)
        'Call the set method of this IntVar with 0 or 1.'

        self.checkbox = Checkbutton(self, variable=self.value)
        self.checkbox.pack(side=LEFT)


class RegisterWidget(Frame):
    '''Display one register.'''

    FORMATS = [
        '%08x',
        (lambda n: (lambda s:    '%s:%s'    % (       s[ :4], s[4: ]       ))('%08x' % n)),
        (lambda n: (lambda s: '%s:%s:%s:%s' % (s[:2], s[2:4], s[4:6], s[6:]))('%08x' % n)),
        '%i',
        hex,
    ]
    '''\
    A list of format strings or callables that are used to convert
    register values to strings for display.
    '''

    def __init__(self, root, label_text, font):
        Frame.__init__(self, root)

        self.current_format = 0
        'Index into the ring buffer of format strings for register label.'

        self._value = 0
        # Cache the int value to enable refresh after changing format.
        
        self.value = StringVar(self)
        'The current text to display.'

        self.set(self._value)

        Label(  # Anonymous label for the register display label.
            self,
            anchor=E,
            font=font,
            text=label_text,
            width=3,
            ).pack(side=LEFT)

        self.label = Entry(
            self,
            font=font,
            textvariable=self.value,
            state="readonly",
            width=12,
            )
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
