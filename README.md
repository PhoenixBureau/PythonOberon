Python Oberon
=============

Some software for [Oberon 2013](http://www.inf.ethz.ch/personal/wirth/ProjectOberon/).

-  [Documentation](https://pythonoberon.readthedocs.io/en/latest/)
-  [Source code](https://git.sr.ht/~sforman/PythonOberon)
-  [Bugs & issues](https://todo.sr.ht/~sforman/python-oberon)


See also:

-  [projectoberon.com](http://projectoberon.com/)
-  [pdewacht/oberon-risc-emu on github](https://github.com/pdewacht/oberon-risc-emu)
-  [Project Oberon emulator in JavaScript and Java](http://schierlm.github.io/OberonEmulator/)
-  [A resource page for Oberon-07](http://oberon07.com/)


A hardware emulator for the new RISC processor written in Python.  If
Pygame is available it will open a screen of the standard dimensions of
1024 x 768 pixels.  I've also implemented a very crude "assembler" which
is really little more than a bunch of helper functions to emit binary
instructions (in the form of 32-bit-wide ints.  However, it also provides
a function dis() that will return a string representing the (integer)
instruction passed to it.

Start with:

```
python -i -m oberon
```

This will use `disk.img` by default.  At around 3400000 cycles the screen
background begins to fill in, and at around 6500000 cycles the window
content begins to be drawn:

![PyGame window showing Oberon](https://git.sr.ht/~sforman/PythonOberon/blob/master/Screenshot.png "PyGame window showing Oberon")

(The `-i` option tells Python to drop into interactive REPL mode after
the script has run.  You can interact with the risc object.)
