.. PythonOberon documentation master file, created by
   sphinx-quickstart on Sun May 12 15:49:46 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


Python Oberon
========================================

An emulator written in Python for the Project Oberon RISC processor.  If
PyGame is available it will open a screen of the standard dimensions of
1024 x 768 pixels.  I've also implemented a very crude "assembler" which
is really little more than a bunch of helper functions to emit binary
instructions (in the form of 32-bit-wide ints.  However, it also provides
a function dis() that will return a string representing the (integer)
instruction passed to it.


.. toctree::
   :maxdepth: 2
   :caption: Module Documentation:

   assembler
   bootloader
   display
   risc
   util


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
