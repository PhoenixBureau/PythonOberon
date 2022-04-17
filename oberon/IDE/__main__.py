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
from sys import argv
import importlib

from oberon.IDE.newcpu import newcpu
from oberon.IDE.widgets import DebugApp


cpu = newcpu()
app = DebugApp(cpu)
app.font['family'] = 'Inconsolata'
app.font['size'] = 14

# app.set_symbols('./symbols.txt')
if '-n' not in argv:
    app.tk.mainloop()


##def newapp():
##    import oberon.IDE.widgets
##    importlib.reload(oberon.IDE.widgets)
##    return oberon.IDE.widgets.DebugApp()
