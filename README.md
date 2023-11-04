Python Oberon
=============

An emulator for [Prof. Wirth's Oberon RISC processor](http://www.inf.ethz.ch/personal/wirth/ProjectOberon/)
ported from Peter De Wachter's emulator written in C (see below.)
There is also a crude assembler.

-  [Documentation](https://pythonoberon.readthedocs.io/en/latest/)
-  [Source code](https://git.sr.ht/~sforman/PythonOberon)
-  [Bugs & issues](https://todo.sr.ht/~sforman/python-oberon)


See also:

-  [projectoberon.com](http://projectoberon.com/)
-  [Project Oberon RISC emulator in C](https://github.com/pdewacht/oberon-risc-emu)
-  [Project Oberon RISC emulator in JavaScript and Java](http://schierlm.github.io/OberonEmulator/)
-  [Project Oberon RISC emulator in Go](https://github.com/fzipp/oberon)
-  [A resource page for Oberon-07](http://oberon07.com/)


Start with:

```
python -i -m oberon emulate
```

- If Pygame is available a screen will open of the standard dimensions of 1024 x 768 pixels.
- This command will use `disk.img` by default.
- At around 3400000 cycles the screen background begins to fill in, and at around 6500000 cycles the window content begins to be drawn:

![PyGame window showing Oberon](https://git.sr.ht/~sforman/PythonOberon/blob/master/Screenshot.png "PyGame window showing Oberon")

(The `-i` option tells Python to drop into interactive REPL mode after
the script has run.  You can interact with the risc object.)

