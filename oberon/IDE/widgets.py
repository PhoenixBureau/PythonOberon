'''
To test run with::
    
    ipython --gui=tk -i -m oberon.IDE -- -n


'''
from Tkinter import (
    Tk,
    Frame,
    LabelFrame,
    Label,
    StringVar,
    LEFT,
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
        regwidg.grid(column=column, row=row)
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

    FORMATS = [
        '%08x',
    ]

    def __init__(self, root, register_number):
        Frame.__init__(self, root)
        
        self.current_format = 0
        'Index into the ring buffer of format strings for register label.'

        self.value = StringVar(self)
        'The current text to display.'

        self.set(0)

        Label(self, text='%x:' % register_number).pack(side=LEFT)
        # Anonymous label for the register display label.

        self.label = Label(self, textvariable=self.value)
        'Display the register value.'
        self.label.pack(side=LEFT)

    def set(self, value):
        '''Given an integer value set the string value of the label.'''
        self.value.set(self.FORMATS[self.current_format] % (value,))
        
