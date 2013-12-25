Python Oberon
=============


Some software for using Oberon 2013.

http://www.inf.ethz.ch/personal/wirth/ProjectOberon/


I am very excited about the latest Oberon version.  I consider it a
Christmas present. In order to bootstrap it I'm writing a hardware
emulator for the new RISC processor using MyHDL, and to get the binary
code to run on the processor I'm writing a simple "transliteration" of
the Oberon Compiler in Python. (the two languages are very syntactically
similar so it is pretty straight forward.)


So far the RISC processor is kinda working.  It seems to handle register
instructions and branches, but there is no support yet for I/O or loading
and storing to RAM (although it fetches instructions from RAM.)  It also
does not properly handle signed numbers in all the places it should.
Additionally the shifters and multiply/divide circuits are omitted for
the moment.


I've implemented a very crude "assembler", which is really little more
than a bunch of helper functions to emit binary instructions (in the form
of 32-bit-wide intbv objects (see the MyHDL docs.)  I hope to circle back
and give it the "Miki Tebeka" treatment (see http://pythonwise.blogspot.com/2012/06/python-based-assembler.html)
later on, but for now this is enough to test and play with the RISC
emulator.


The compiler can be exercised by running the test\_parser.py script which
compiles the Amodule.Mod.txt demo Oberon source into binary.  As a side
effect it will create two files: Amodule.smb and Amodule.rsc, which you
must delete in order to run the compiler again without it complaining
about overwriting them.  This is by design.

There are bound to be more bugs in the Python compiler code as I doubt
the demo Oberon source exercises all the code paths.  It has been very
entertaining and educational going through the Oberon source for the
Oberon compiler line-by-line.
