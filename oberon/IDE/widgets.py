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

    Button,
    Checkbutton,
    Entry,
    Frame,
    IntVar,
    Label,
    LabelFrame,
    Listbox,
    Scrollbar,
    StringVar,
    Text,

    BOTH,
    LEFT,
    RIGHT,
    SUNKEN,
    E,
    END,
    N,
    S,
    LEFT,
    VERTICAL,
    W,
    X,
    Y,
    )
import tkFont, tkFileDialog, tkMessageBox

from glob import iglob
from os import getcwd
from os.path import exists, join, split, splitext
from pickle import load, dump
from StringIO import StringIO

from oberon.IDE.newcpu import newcpu


_DEFAULT_GRID_OPTS = dict(sticky=N+E+W+S, padx=3, pady=3)


class DebugApp(object):
    '''damn'''

    def __init__(self, cpu=None):

        if cpu is None:
            cpu = newcpu()
            cpu.decode(0)  # Ensure that all attributes of the cpu have been created.
        self.cpu = cpu

        self.tk = Tk()
        self.font = tkFont.Font(family='Courier', size=8)
        self.frame = Frame(self.tk)
        self.frame.pack()

        self.register_frame = LabelFrame(self.frame, text='Registers', font=self.font)

        self.register_widgets = [
            self._register(self.register_frame, 'R%i' % i, i // 8, i % 8)
            for i in xrange(16)
        ]

        self.specials = LabelFrame(self.frame, text='Specials', font=self.font)

        self.PC = self._register(self.specials, 'PC:')
        self.H = self._register(self.specials, 'H:', row=1)

        self.N = self._flag(self.specials, 'N:', column=1)
        self.Z = self._flag(self.specials, 'Z:', column=2)
        self.C = self._flag(self.specials, 'C:', column=1, row=1)
        self.OV = self._flag(self.specials, 'OV:', column=2, row=1)

        self.pj = PickleJar(self, self.font, )

        self._make_controls()
        self._make_ram_inspector()
        
        self.register_frame.grid(column=0, row=0, **_DEFAULT_GRID_OPTS)
        self.specials.grid(column=0, row=1, **_DEFAULT_GRID_OPTS)
        self.pj.grid(column=0, row=2, **_DEFAULT_GRID_OPTS)
        self.controls.grid(column=1, row=2, **_DEFAULT_GRID_OPTS)
        self.ram_inspector.grid(column=1, row=0, **_DEFAULT_GRID_OPTS)

        self.copy_cpu_values()

    def _make_ram_inspector(self):
        self.ram_inspector = LabelFrame(self.frame, text='RAM', font=self.font)
        self._ram_text_widget = Text(
            self.ram_inspector,
            font=self.font,
            height=13,
            width=68,
            )
        self._ram_text_widget.pack(expand=True, fill=BOTH)

    def _update_ram_inspector(self):
        s = StringIO()
        self.cpu.dump_mem(to_file=s, number=6)
        self._ram_text_widget.delete('0.0', END)
        self._ram_text_widget.insert(END, s.getvalue())

    def _make_controls(self):
        self.tk.bind('<space>', self.step)
        self.controls = Frame(self.frame)
        self.step_button = Button(
            self.controls,
            text='Step',
            font=self.font,
            command=self.step,
        )
        self.save_button = Button(
            self.controls,
            text='Save',
            font=self.font,
            command=self.pj.save_pickle,
        )
        self.step_button.pack()
        self.save_button.pack()

    def step(self, event=None):
        self.cpu.cycle()
        self.copy_cpu_values()

    def _register(self, frame, register_number, column=0, row=0):
        regwidg = RegisterWidget(frame, register_number, self.font)
        regwidg.grid(column=column, row=row, sticky=W)
        return regwidg

    def _flag(self, frame, label, column=0, row=0):
        flagwidg = FlagWidget(frame, label, self.font)
        flagwidg.grid(column=column, row=row, sticky=W)
        return flagwidg

    def copy_cpu_values(self):
        for reg, regwidg in zip(self.cpu.R, self.register_widgets):
            regwidg.set(reg)
        self.PC.set(self.cpu.PC)
        self.H.set(self.cpu.H)
        self.N.set(self.cpu.N)
        self.Z.set(self.cpu.Z)
        self.C.set(self.cpu.C)
        self.OV.set(self.cpu.OV)
        self._update_ram_inspector()


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

        self.set = self.value.set

        self.checkbox = Checkbutton(self, variable=self.value)
        self.checkbox.pack(side=LEFT)


class RegisterWidget(Frame):
    '''Display one register.'''

    FORMATS = [
        '%08x',
        (lambda n: (lambda s:    '%s:%s'    % (       s[ :4], s[4: ]       ))('%08x' % n)),
        (lambda n: (lambda s: '%s:%s:%s:%s' % (s[:2], s[2:4], s[4:6], s[6:]))('%08x' % n)),
        '%i',
        (lambda n: hex(n).rstrip('Ll')),
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


class PickleJar(Frame):
    '''Manage the directory of saved states.'''

    def __init__(self, app, font, save_dir=None):
        Frame.__init__(self, app.frame)
        self.app = app

        self.frame = LabelFrame(self, text='Saved States', font=font)
        self.frame.pack(expand=True, fill=BOTH)

        self.current_dir = StringVar(self.frame)
        self.current_dir_entry = Entry(
            self.frame,
            font=font,
            textvariable=self.current_dir,
            state="readonly",
            width=24,
        )

        self.set_current_dir(getcwd() if save_dir is None else save_dir)

        self.current_dir_entry.bind('<Button-3>', self.pick_save_dir)

        self.lb = ScrollingListbox(self.frame, font, height=6)
        self.lb.listbox.bind('<Double-Button-1>', self.load_pickle)

        self.current_dir_entry.pack(expand=True, fill=X)
        self.lb.pack(expand=True, fill=BOTH)

        self.populate_pickles()

    def set_current_dir(self, save_dir):
        assert exists(save_dir)
        self.save_dir = save_dir
        self.current_dir.set(self.save_dir)
        # The interesting bit is at the right end of the string.
        self.current_dir_entry.xview(len(self.save_dir))

    def populate_pickles(self):
        self.pickles = {
            self._per_pickle_files(f): f
            for f in iglob(join(self.save_dir, '*.pickle'))
        }
        self.lb.variable.set(' '.join(sorted(self.pickles)))

    @staticmethod
    def _per_pickle_files(filename):
        _, fn = split(filename)
        pickle_name, _ = splitext(fn)
        return pickle_name

    def pick_save_dir(self, event=None):
        save_dir = tkFileDialog.askdirectory(
            initialdir=self.save_dir,
            mustexist=True,
        )
        if save_dir:
            self.set_current_dir(save_dir)
            self.populate_pickles()

    def load_pickle(self, event=None):
        index = self.lb.listbox.curselection()
        if not index:
            return
        pickle_fn = self.lb.listbox.get(index[0])
        fn = join(self.save_dir, pickle_fn + '.pickle')
        with open(fn, 'rb') as f:
            new_cpu = load(f)
        self.app.cpu = new_cpu
        self.app.copy_cpu_values()

    def save_pickle(self, event=None):
        fn = tkFileDialog.asksaveasfilename(
            initialdir=self.save_dir,
            initialfile='Untitled.pickle',
            title='Save to...',
            filetypes=(('Pickle files', '*.pickle'),),
        )
        if not fn:
            return
        print 'saving', fn
        with open(fn, 'wb') as f:
            dump(self.app.cpu, f)
        # if the fn is in save_dir...
        self.populate_pickles()


class ScrollingListbox(Frame):

    def  __init__(self, root, font, **kw):
        Frame.__init__(self, root, bd=2, relief=SUNKEN)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.variable = StringVar(self)
        self.scrollbar = Scrollbar(self)
        self.listbox = Listbox(
            self,
            bd=0,
            listvariable=self.variable,
            yscrollcommand=self.scrollbar.set,
            **kw
        )
        self.scrollbar.config(command=self.listbox.yview)
        self.listbox.grid(row=0, column=0, sticky=N+E+W+S)
        self.scrollbar.grid(row=0, column=1, sticky=N+E+S)
