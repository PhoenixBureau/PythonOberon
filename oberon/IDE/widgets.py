# -*- coding: utf-8 -*-
#
#    Copyright © 2019 Simon Forman
#
#    This file is part of PythonOberon
#
#    PythonOberon is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    PythonOberon is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with PythonOberon.  If not see <http://www.gnu.org/licenses/>.
#
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
from tkinter import (
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
import tkinter.font, tkinter.filedialog, tkinter.messagebox

from glob import iglob
from os import getcwd
from os.path import exists, join, split, splitext
from pickle import load, dump
from io import StringIO
from traceback import print_exc

from oberon.IDE.newcpu import newcpu
from oberon.risc import ROMStart, MemSize, MemWords


_DEFAULT_GRID_OPTS = dict(
    sticky=N + E + W + S, padx=1, pady=1, ipadx=3, ipady=3
)


class DebugApp(object):
    '''damn'''

    def __init__(self, cpu=None):
        self.cpu = cpu if cpu is not None else newcpu()

        self.tk = Tk()
        self.tk.title('Oberon RISC Emulator')
        self.font = tkinter.font.Font(family='Courier', size=8)
        self.frame = Frame(self.tk)
        self.frame.pack()

        self.register_frame = LabelFrame(
            self.frame, text='Registers', font=self.font
        )

        self.register_widgets = [
            self._register(self.register_frame, 'R%i' % i, i // 8, i % 8)
            for i in range(16)
        ]

        self.specials = LabelFrame(
            self.frame, text='Specials', font=self.font
        )

        self.PC = self._register(self.specials, 'PC:')
        self.H = self._register(self.specials, 'H:', row=1)

        self.N = self._flag(self.specials, 'N:', column=1)
        self.Z = self._flag(self.specials, 'Z:', column=2)
        self.C = self._flag(self.specials, 'C:', column=1, row=1)
        self.OV = self._flag(self.specials, 'OV:', column=2, row=1)

        self.pj = PickleJar(self, self.font)
        self._make_controls()
        self.ram_inspector = RAMInspector(self.frame, self.font)
        self.breakpoints = Breakpoints(self.frame, self.font)
        self.watch = Watch(self.frame, self.font)
        self.LEDs = LEDsAndSwitches(self, self.font)
        self._break = False

        # Bind from here to pass cpu.
        self.watch.text.bind(
            '<Button-3>', lambda _: self.watch.update(self.cpu, self.syms)
        )
        self.breakpoints.text.bind(
            '<Button-3>',
            lambda _: self.breakpoints.check(self.cpu, self.syms),
        )

        self.register_frame.grid(column=0, row=0, **_DEFAULT_GRID_OPTS)
        self.specials.grid(column=0, row=1, **_DEFAULT_GRID_OPTS)
        self.LEDs.frame.grid(column=0, row=2, **_DEFAULT_GRID_OPTS)
        self.pj.grid(column=0, row=3, **_DEFAULT_GRID_OPTS)
        self.ram_inspector.grid(
            column=1, row=0, columnspan=2, **_DEFAULT_GRID_OPTS
        )
        self.breakpoints.grid(
            column=1, row=1, rowspan=2, **_DEFAULT_GRID_OPTS
        )
        self.controls.grid(column=1, row=3, **_DEFAULT_GRID_OPTS)
        self.watch.grid(column=2, row=1, rowspan=2, **_DEFAULT_GRID_OPTS)

        self.watch.reset_text(self.cpu.watches)
        self.breakpoints.reset_text(self.cpu.breakpoints)

        self.syms = {}
        self.data_addrs = set()

        self.copy_cpu_values()

    def _make_controls(self):
        self.tk.bind('<Control-space>', self.step)
        self.controls = Frame(self.frame)
        self.step_button = Button(
            self.controls,
            text='>',
            font=self.font,
            command=lambda: self._step(),
        )
        self.step10_button = Button(
            self.controls,
            text='10 >>',
            font=self.font,
            command=lambda: self._step(10),
        )
        self.step104_button = Button(
            self.controls,
            text='1,000,000 >>',
            font=self.font,
            command=lambda: self._step(10**6),
        )
        self.save_button = Button(
            self.controls,
            text='Save',
            font=self.font,
            command=self.pj.save_pickle,
        )
        self.step_button.pack(side=LEFT)
        self.step10_button.pack(side=LEFT)
        self.step104_button.pack(side=LEFT)
        self.save_button.pack(side=LEFT)

    def set_symbols(self, symbol_table, data_addrs):
        syms = {}
        for name, address in symbol_table.items():
            # syms[int(address) >> 2] = name
            syms[address >> 2] = name
        self.syms = syms
        self.data_addrs = data_addrs

    ##        self.copy_cpu_values()

    def step(self, event=None):
        if not self._break:
            self._step()

    def _step(self, n=1):
        self._break = False
        for _ in range(n):
            self.cpu.cycle()
            if self.breakpoints.check(self.cpu, self.syms):
                self._break = True
                break
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
        self.ram_inspector.update(self.cpu, self.syms)
        self.watch.update(self.cpu, self.syms)
        self.LEDs.update(self.cpu)


class LabelText(LabelFrame):
    def __init__(self, root, label, font, **kw):
        LabelFrame.__init__(self, root, text=label, font=font)
        self.text = Text(self, font=font, relief='flat', **kw)
        self.text.pack(expand=True, fill=BOTH)

    def reset_text(self, text):
        self.text.delete('0.0', END)
        self.text.insert(END, text)


class RAMInspector(LabelText):
    def __init__(self, root, font):
        LabelText.__init__(self, root, 'RAM', font, height=13, width=80)

    def update(self, cpu, syms):
        s = StringIO()
        cpu.dump_mem(to_file=s, number=6, syms=syms)
        self.reset_text(s.getvalue())


class Watch(LabelText):

    ERR = 'watch_error'  # Text tag name.

    def __init__(self, root, font):
        self.font = font
        LabelText.__init__(self, root, 'Watch', font, height=5, width=34)
        self.text['wrap'] = 'none'  # TODO: scrollbars
        self.watches = []
        self.text.tag_config(
            self.ERR, background='red', bgstipple='gray25'
        )

    def update(self, cpu, syms):
        d = dict(cpu.__dict__)
        for addr, label in syms.items():
            d[label] = addr << 2
        d['ROMStart'] = ROMStart

        self.text.tag_remove(
            self.ERR, '0.0', END
        )  # Clear any error tags.
        text = cpu.watches = self.text.get('0.0', END).rstrip()
        exprs = text.splitlines()

        num_exprs = len(exprs)
        if not (
            num_exprs
            == len(self.watches)
            == len(self.text.window_names())
        ):
            while self.watches:
                self.watches.pop().destroy()
            for line_no in range(1, 1 + num_exprs):
                e = RegisterWidget(
                    self.text, str(line_no) + ':', self.font
                )
                self.watches.append(e)
                self.text.window_create('%i.0' % line_no, window=e)

        for line_no, (e, expr) in enumerate(zip(self.watches, exprs), 1):
            self._update_widget(d, line_no, e, expr)

    def _update_widget(self, d, line_no, e, expr):
        if (not expr) or expr.isspace():
            e.set(0)
            return
        try:
            value = eval(expr, d)
        except:
            self._err_tag_line(line_no)
            print_exc()
            value = 0
        e.set(value)

    def _err_tag_line(self, line_no):
        self.text.tag_add(
            self.ERR, '%i.0' % line_no, '%i.0' % (line_no + 1)
        )

    def reset_text(self, text):
        LabelText.reset_text(self, text)
        self.watches = []


class Breakpoints(LabelText):

    BRK = 'break_break'  # Text tag names.
    ERR = 'break_error'

    def __init__(self, root, font):
        LabelText.__init__(
            self, root, 'Breakpoints', font, height=5, width=34
        )
        self.text.tag_config(self.BRK, background='orange')
        self.text.tag_config(
            self.ERR, background='red', bgstipple='gray25'
        )

    def check(self, cpu, syms):
        d = dict(cpu.__dict__)
        for addr, label in syms.items():
            d[label] = addr
        d['ROMStart'] = ROMStart
        self.text.tag_remove(self.BRK, '0.0', END)  # Clear any tags.
        self.text.tag_remove(self.ERR, '0.0', END)
        text = cpu.breakpoints = self.text.get('0.0', END).rstrip()
        for line_no, e in enumerate(text.splitlines(), 1):
            if not e.strip():
                continue  # filter blank lines.
            try:
                value = eval(e, d)
            except:
                self._tag_line(line_no, self.ERR)
                print_exc()
                return True
            if value:
                self._tag_line(line_no, self.BRK)
                return True
        return False

    def _tag_line(self, line_no, tag):
        self.text.tag_add(tag, '%i.0' % line_no, '%i.0' % (line_no + 1))


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
        ).pack(
            side=LEFT
        )

        self.value = IntVar(self, value=0)
        'Call the set method of this IntVar with 0 or 1.'

        self.set = self.value.set

        self.checkbox = Checkbutton(self, variable=self.value)
        self.checkbox.pack(side=LEFT)


class RegisterWidget(Frame):
    '''Display one register.'''

    FORMATS = [
        '%08x',
        (lambda n: (lambda s: '%s:%s' % (s[:4], s[4:]))('%08x' % n)),
        (
            lambda n: (
                lambda s: '%s:%s:%s:%s' % (s[:2], s[2:4], s[4:6], s[6:])
            )('%08x' % n)
        ),
        '%i',
        (lambda n: hex(n).rstrip('Ll')),
        (lambda n: (lambda s: f'{chr(int(s[4:6],16))}{chr(int(s[2:4],16))}{chr(int(s[:2],16))}:{s[6:]}')(f'{n:08x}'))
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

        if isinstance(formatter, str):
            label = formatter % (value,)
        elif callable(formatter):
            label = formatter(value)
        else:
            raise TypeError('wtf')

        self.value.set(label)

    def toggle_format(self, event=None):
        '''Switch to the next formatter.'''
        self.current_format = (self.current_format + 1) % len(
            self.FORMATS
        )
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
        save_dir = tkinter.filedialog.askdirectory(
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
        self.app.watch.reset_text(new_cpu.watches)
        self.app.breakpoints.reset_text(new_cpu.breakpoints)
        self.app.LEDs._monkey_patch_LED_write(new_cpu)
        self.app.copy_cpu_values()

    def save_pickle(self, event=None):
        fn = tkinter.filedialog.asksaveasfilename(
            initialdir=self.save_dir,
            initialfile='Untitled.pickle',
            title='Save to...',
            filetypes=(('Pickle files', '*.pickle'),),
        )
        if not fn:
            return
        print('saving', fn)
        self.app.LEDs._unpatch(self.app.cpu)
        with open(fn, 'wb') as f:
            dump(self.app.cpu, f)
        self.app.LEDs._monkey_patch_LED_write(self.app.cpu)
        # if the fn is in save_dir...
        self.populate_pickles()


class LEDsAndSwitches(object):
    def __init__(self, app, font):
        self.app = app
        self.frame = LabelFrame(
            app.frame,
            text='LEDs and Switches',
            font=font,
        )
        self.LEDs = []
        self.switches = []
        for column in range(8):
            LED_var = IntVar(self.frame)
            LED = Checkbutton(
                self.frame,
                indicatoron=0,
                selectcolor='#8080ff',
                text=str(column),
                variable=LED_var,
            )
            LED.bind('<Button-1>', lambda _: 'break')  # Output only.
            LED.grid(row=0, column=7 - column)

            switch_var = IntVar(self.frame)
            switch = Checkbutton(
                self.frame,
                command=(lambda i=column: self._set_switch(i)),
                variable=switch_var,
            )
            switch.grid(row=1, column=7 - column)

            self.LEDs.append(LED_var)
            self.switches.append(switch_var)

        self._monkey_patch_LED_write(self.app.cpu)

    def _monkey_patch_LED_write(self, cpu):
        cpu.io_ports[4].write = self.set_LEDs

        # Since we are initializing a new CPU here, let's reset our LEDs.
        self.set_LEDs(0)

    @staticmethod
    def _unpatch(cpu):
        device = cpu.io_ports[4]
        if 'write' in device.__dict__:
            del device.write

    def update(self, cpu):
        # Even though cpu should be self.app.cpu pass a cpu in.
        self.set_switches(cpu.io_ports[4].switches)

    def set_LEDs(self, value):
        i = 1
        for led in self.LEDs:
            led.set(bool(value & i))
            i <<= 1

    def set_switches(self, value):
        i = 1
        for switch in self.switches:
            switch.set(bool(value & i))
            i <<= 1

    def _set_switch(self, i):
        assert 0 <= i < 8
        if self.switches[i].get():  # Switch is on.
            self.app.cpu.io_ports[4].switches |= 1 << i
        else:
            self.app.cpu.io_ports[4].switches &= 0xFF ^ (1 << i)
        print('switches', bin(self.app.cpu.io_ports[4].switches))


class ScrollingListbox(Frame):
    def __init__(self, root, font, **kw):
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
            **kw,
        )
        self.scrollbar.config(command=self.listbox.yview)
        self.listbox.grid(row=0, column=0, sticky=N + E + W + S)
        self.scrollbar.grid(row=0, column=1, sticky=N + E + S)
