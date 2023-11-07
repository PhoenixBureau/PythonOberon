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
from argparse import ArgumentParser, FileType
from sys import argv
import importlib

from oberon.util import load_syms
from oberon.IDE.newcpu import newcpu
from oberon.IDE.widgets import DebugApp
from pkg_resources import resource_filename


DISKIMG = resource_filename(__name__, '../disk.img')


parser = ArgumentParser(
    prog='python -m oberon.IDE',
    #usage='python -i -m oberon [-d DISK_IMAGE]',
    description='An emulator for Prof Wirth\'s RISC CPU for Project Oberon.',
    )
parser.add_argument(
    'disk',
    type=FileType('rb'),
    default=DISKIMG,
    )
parser.add_argument(
    '-b', '--binary',
    type=FileType('rb'),
    )
##asm_subparser.add_argument(
##    'output',
##    type=FileType('wb'),
##    )
parser.add_argument(
    '-s', '--symbol-file',
    type=FileType('rb'),
    )
parser.add_argument(
    '-k', '--breakpoints-file',
    type=FileType('r'),
    )
parser.add_argument(
    '-w', '--watches-file',
    type=FileType('r'),
    )

args = parser.parse_args()

arg_ = {}
if args.breakpoints_file:
    arg_['breakpoints'] = args.breakpoints_file.read()
if args.watches_file:
    arg_['watches'] = args.watches_file.read()
cpu = newcpu(
    disk_file=args.disk,
    serial_input_file=args.binary,
    **arg_
    )
app = DebugApp(cpu)
if args.symbol_file:
    app.set_symbols(*load_syms(args.symbol_file))
app.font['family'] = 'DejaVu Sans Mono'
app.font['size'] = 12
if '-n' not in argv:
    app.tk.mainloop()


##def newapp():
##    import oberon.IDE.widgets
##    importlib.reload(oberon.IDE.widgets)
##    return oberon.IDE.widgets.DebugApp()
