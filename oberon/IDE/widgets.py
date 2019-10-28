'''

Experimental GUI
========================

To test run with::
    
    ipython --gui=tk -i -m oberon.IDE -- -n

Let's break that down.  We're using ``ipython``.  The ``--gui=tk`` CLI option
tells it to use the ``Tkinter``-compatible event loop, ``-i`` tells it to drop
into interactive mode after the script ends rather than exiting,
``-m oberon.IDE`` tells it to
use the ``oberon.IDE.__main__`` module as the script to run, and ``--`` tells
it to pass the rest of the CLI options to the script itself.  The ``-n`` CLI
option is detected by the main script and prevents it from starting the
Tkinter mainloop on its own.

The combination of using IPython's ``Tkinter``-compatible event loop and not
calling the Tkinter mainloop in the main script lets you use IPython shell
while the GUI runs and updates.  This is really flexible and powerful, as
you have all of Python available to work with, but you have to read the
source and know something about Python and Tkinter GUI code to take
advantage of it.

For example, the main script creates the app and puts it in a variable ``w``,
and you can change the `font properties <https://effbot.org/tkinterbook/tkinter-widget-styling.htm#fonts>`_ like this::

    In [1]: w.font['family'] = 'Iosevka Term'

    In [2]: w.font['size'] = 12


'''
from Tkinter import (
    Tk,

    Checkbutton,
    Entry,
    Frame,
    IntVar,
    Label,
    LabelFrame,
    Listbox,
    Scrollbar,
    StringVar,

    E,
    N,
    S,
    LEFT,
    VERTICAL,
    W,
    )
import tkFont
import tkFileDialog

from glob import iglob
from os import getcwd
from os.path import exists, join, split, splitext


class DebugApp(object):
    '''damn'''

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

        self.pj = PickleJar(self.frame, self.font, )

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


class PickleJar(object):
    '''Manage the directory of saved states.'''

    def __init__(self, frame, font, save_dir=None):
        self.frame = LabelFrame(frame, text='Saved States')
        self.frame.pack()

        self.save_dir = getcwd() if save_dir is None else save_dir
        assert exists(self.save_dir)

        self.current_dir = StringVar(self.frame)
        self.current_dir.set(self.save_dir)
        self.current_dir_entry = Entry(
            self.frame,
            font=font,
            textvariable=self.current_dir,
            state="readonly",
            width=24,
            )
        self.current_dir_entry.xview(len(self.save_dir))
        self.current_dir_entry.pack()
        self.current_dir_entry.bind('<Button-3>', self.pick_save_dir)

        self.make_listbox(font).pack(expand=True, fill='both')
        self.populate_pickles()

    def make_listbox(self, font):
        lb_frame = Frame(self.frame)
        self.lb_yScroll = Scrollbar(lb_frame, orient=VERTICAL)
        self.lb_val = StringVar(lb_frame)
        self.lb = Listbox(
            lb_frame,
            listvariable=self.lb_val,
            font=font,
            height=6,
            yscrollcommand=self.lb_yScroll.set
            )
        self.lb_yScroll['command']= self.lb.yview
        self.lb.grid(row=0, column=0, sticky=N+E+W+S)
        self.lb_yScroll.grid(row=0, column=1, sticky=N+S)
        return lb_frame

    def populate_pickles(self):
        self.pickles = {
            self._per_pickle_files(f): f
            for f in iglob(join(self.save_dir, '*.pickle'))
        }
        self.lb_val.set(' '.join(sorted(self.pickles)))

    def _per_pickle_files(self, filename):
        _, fn = split(filename)
        pickle_name, _ = splitext(fn)
        return pickle_name

    def pick_save_dir(self, event=None):
        save_dir = tkFileDialog.askdirectory(
            initialdir=self.save_dir,
            mustexist=True,
        )
        if save_dir:
            self.save_dir = save_dir
            self.current_dir.set(self.save_dir)
            self.current_dir_entry.xview(len(self.save_dir))
            self.populate_pickles()
