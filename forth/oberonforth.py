#
#    Copyright © 2022 Simon Forman
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
   ___  _                        ___        _   _
  / _ \| |__  ___ _ _ ___ _ _   | __|__ _ _| |_| |_
 | (_) | '_ \/ -_) '_/ _ \ ' \  | _/ _ \ '_|  _| ' \
  \___/|_.__/\___|_| \___/_||_| |_|\___/_|  \__|_||_|

  Oberon Forth

Now that I have an emulator and assembler the obvious thing to do is
implement a Forth.  I grabbed a copy of Jonesforth and set to.

This isn't going to be standard or complete.  It's first job is to
exercise the emulator and assembler.  It's second job is to stand in
between the machine & machine code on one side, and the higher-level
interface and language(s) on the other, and bridge the gap.
It's also just fun and cool.  Forth is awesome.  C. Moore is a genius.

Misc details:

- The cell size is 4-byte word.
- It doesn't use the built-in return stack machinery (R15)
  (Although I do define a couple of small routines after Jones Forth,
  they don't make any calls themselves so the "return stack" is just the
  R15 register.)
- It only stores the first three characters of word names.  Plus the
  length, that's all the information FIND has.  Beware!
- It reads input from the serial port (because PS2 keyboards are a bit
  more complex than a stream of bytes.  It would be nice to support the
  keyboard eventually.)
- It doesn't support BASE, all integer literals start with '$' and
  consist of 0-9a-f (no uppercase!) hex.
- A simple 8x13 pixel font is loaded into RAM just below the display
  space.  (See paint_char and pai below.)
- It would be fun to do a direct-threaded version using the return
  stack machinery (R15).
-


(
    $00 $01 $02 $03 $04 $05 $06 $07 $08 $09 $0A $0B $0C $0D $0E $0F
$00  00  01  02  03  04  05  06  07  08  09  0A  0B  0C  0D  0E  0F
$10  10  11  12  13  14  15  16  17  18  19  1A  1B  1C  1D  1E  1F
$20  20   !   "   #   $   %   &   '   (   )   *   +   ,   -   .   /
$30   0   1   2   3   4   5   6   7   8   9   :   ;   <   =   >   ?
$40   @   A   B   C   D   E   F   G   H   I   J   K   L   M   N   O
$50   P   Q   R   S   T   U   V   W   X   Y   Z   [   \   ]   ^   _
$60   `   a   b   c   d   e   f   g   h   i   j   k   l   m   n   o
$70   p   q   r   s   t   u   v   w   x   y   z   {   |   }   ~   7F

)

'''

# In re: the FIGlet banners, I use: http://www.patorjk.com/software/taag/

# (My eyesight is not great, I lost my glasses, and I'm using
# a TV as a monitor, so I use these FIGlet banners to help me
# navigate.  Normally code has a lot of visual structure that
# helps with that, but asm is linear.)


# The chip uses two's complement.
def s_to_u_32(n):
    '''
    Signed Python int to 32-bit signed C int.
    '''
    assert -0x8000_0000 <= n <= 0x7fff_ffff
    return n & 0xffff_ffff


##    _                     _    _
##   /_\   ______ ___ _ __ | |__| |___ _ _
##  / _ \ (_-<_-</ -_) '  \| '_ \ / -_) '_|
## /_/ \_\/__/__/\___|_|_|_|_.__/_\___|_|
## \ \ / /_ _ _ _(_)__ _| |__| |___ ___
##  \ V / _` | '_| / _` | '_ \ / -_|_-<
##   \_/\__,_|_| |_\__,_|_.__/_\___/__/
#
# Assembler Variables

# Put these anywhere...
DATA_STACK = 0x4000
RETURN_STACK = 0x6000

# Registers
R0, R1, R2 = 0, 1, 2
next_function = 3
codeword = 4
word_counter = 5
word_pointer = 6
IP = 14
Dstack = 10
Rstack = 12

# Flags
F_IMMED = 0x80  #   0b0_1000_0000
F_HIDDEN = 0x20  #  0b0_0010_0000
F_LENMASK = 0x1f  # 0b0_0001_1111

FIND_MASK = 0xFFFFFFFF ^ F_IMMED
# 0b0_11111111_11111111_11111111_01111111

# I/O
SERIAL_PORT = s_to_u_32(-56)  # io_ports[8]
SERIAL_STATUS = s_to_u_32(-52)  # io_ports[12]

# Dictionary
LINK = 0


##  __  __
## |  \/  |__ _ __ _ _ ___ ___
## | |\/| / _` / _| '_/ _ (_-<
## |_|  |_\__,_\__|_| \___/__/
#
# Macros

def NEXT():
    T_imm(NEXT_)


def PUSHRSP(reg):
    '''push reg on to return stack'''
    Sub_imm(Rstack, Rstack, 4)  # Rstack -= 4
    Store_word(reg, Rstack)     # reg -> RAM[Rstack]


def POPRSP(reg):
    '''pop top of return stack to reg'''
    Load_word(reg, Rstack)      # reg <- RAM[Rstack]
    Add_imm(Rstack, Rstack, 4)  # Rstack += 4


def PUSH(reg):
    '''push reg onto stack'''
    Sub_imm(Dstack, Dstack, 4)  # Dstack -= 4
    Store_word(reg, Dstack)     # reg -> RAM[Dstack]


def POP(reg):
    '''pop top of stack to reg'''
    Load_word(reg, Dstack)      # reg <- RAM[Dstack]
    Add_imm(Dstack, Dstack, 4)  # Dstack += 4


def POKE(reg):
    '''
    Store reg to top of stack without changing stack pointer.
    '''
    Store_word(reg, Dstack)     # reg -> RAM[Dstack]


def PEEK(reg):
    '''
    Load top of stack to register without changing stack pointer.
    '''
    Load_word(reg, Dstack)      # reg <- RAM[Dstack]


def def_(name, LABEL, flags=0):
    '''
    Set up dictionary link, name field, and label for word definitions.
    '''
    assert isinstance(name, bytes)
    # To make a label based off the name of some other label you have to
    # grab the globals() object, which is the context object of the
    # assembler, and access the new label name to create a new LabelThunk.
    label(globals()[LABEL.name + '_dfa'])
    global LINK
    dw(LINK)
    LINK = HERE() - 4
    name_len = len(name)
    assert name_len < 32, repr(name)
    name_bytes = [name_len | flags]
    name_bytes.extend(name)  # Converts bytes to [int].
    while len(name_bytes) % 4: name_bytes.append(0)
    for i in range(0, len(name_bytes), 4):
        d, c, b, a = name_bytes[i:i+4]
        dw((a<<24) + (b<<16) + (c<<8) + d)
        break  # We are only using the count and first three letters
               # to distinguish words.  This makes some things easier
               # to implement without imposing an unduly restrictive
               # burden on the namer-of-new-words.
    label(LABEL)


def defword(name, LABEL, flags=0):
    '''
    Define a colon word.
    '''
    def_(name, LABEL, flags)
    dw(DOCOL)  # codeword points to DOCOL colon word mini-interpreter.


def defcode(name, LABEL, flags=0):
    '''
    Define a primitive ASM word.
    '''
    def_(name, LABEL, flags)
    dw(HERE() + 4)  # codeword points to ASM immediately following.


def defvar(name, LABEL, flags=0, initial=0):
    '''
    Define a variable word.
    '''
    LABEL_var = globals()[LABEL.name + '_var']
    defcode(name, LABEL, flags)
    # Put the address of the variable on the stack.
    Mov_imm(R0, LABEL_var)
    # We will not be allocating so many words that the "_var" address
    # will ever be large enough to invalidate the above instruction.
    PUSH(R0)
    NEXT()
    # Reserve a word of RAM for the variable.
    label(LABEL_var)
    dw(initial)

def defconst(name, LABEL, value, flags=0):
    defcode(name, LABEL, flags)
    move_immediate_word_to_register(R0, value)
    PUSH(R0)
    NEXT()

def move_immediate_word_to_register(reg, word):
    # TODO: check size & sign of word value?
    Mov_imm(reg, HIGH(word), u=1)
    Ior_imm(reg, reg, LOW(word))


def busywait_on_serial_ready():
    '''Call the _KEY subroutine.'''
    Mov_imm(R1, _KEY)
    T_link(R1)


def HIGH(i):
    return (i >> 16) & 0xFFFF


def LOW(i):
    return i & 0xFFFF


negative_offset_24 = lambda n: s_to_u_32(n) & 0xffffff
negative_offset_20 = lambda n: s_to_u_32(n) & 0x0fffff


##  _              _
## | |__  ___ __ _(_)_ _
## | '_ \/ -_) _` | | ' \
## |_.__/\___\__, |_|_||_|
##           |___/
#
# The bootloader stores a couple of system constants to the RAM in the
# first few words.  Specifically:
#     MemLim = 0E7EF0H; stackOrg = 80000H;
#     SYSTEM.PUT(12, MemLim);
#     SYSTEM.PUT(24, stackOrg);
#
# Any code in those locations will be clobbered!  So the first thing to
# do is put a branch instruction there to GOTO main, then reserve some
# space for the bootloader (I forget why 36 bytes instead of 24.)

T_imm(main)
label(_reserved, reserves=36)


label(NEXT_)
Load_word(next_function, IP)        # next_function <- RAM[IP]
Load_word(codeword, next_function)  # codeword <- RAM[next_function]
Add_imm(IP, IP, 4)                  # IP += 4
T(codeword)                         # PC <- RAM[codeword]


##  ___   ___   ___ ___  _
## |   \ / _ \ / __/ _ \| |
## | |) | (_) | (_| (_) | |__
## |___/ \___/ \___\___/|____|
#
# "Do Colon Definition"
# This is the common behaviour for all colon-defined Forth words.
# It inserts its body list into the pending evaluation stack, I mean the
# return stack.

label(DOCOL)
PUSHRSP(IP)  # Save current value of IP to the Return Stack.
# Make IP point from the codeword to the first data word.
Add_imm(IP, next_function, 4)
NEXT()


##             _
##  _ __  __ _(_)_ _
## | '  \/ _` | | ' \
## |_|_|_\__,_|_|_||_|

label(main)
Mov_imm(Dstack, DATA_STACK)
Mov_imm(Rstack, RETURN_STACK)
Mov_imm(IP, cold_start)
NEXT()


##         _    _      _            _
##  __ ___| |__| |  __| |_ __ _ _ _| |_
## / _/ _ \ / _` | (_-<  _/ _` | '_|  _|
## \__\___/_\__,_|_/__/\__\__,_|_|  \__|
##              |___|
label(cold_start)
dw(REPL)  # IP set to point here at start
# so this RAM address must contain the address
# of the codeword of REPL.


##                    _
## __ __ _____ _ _ __| |___
## \ V  V / _ \ '_/ _` (_-<
##  \_/\_/\___/_| \__,_/__/

defword(b'REPL', REPL)
dw(INTERPRET)
dw(BRANCH)
dw(s_to_u_32(-8))  # Loop back to INTERPRET.


defcode(b'DROP', DROP)
Add_imm(Dstack, Dstack, 4)  # drop top of stack
NEXT()


defcode(b'EXIT', EXIT)
POPRSP(IP)  # Restore previous IP from the Return Stack.
NEXT()


defcode(b'LIT', LIT)
Load_word(R0, IP)   # Don't run the next cell, load it,
PUSH(R0)            # push the value,
Add_imm(IP, IP, 4)  # then skip it.
NEXT()


defcode(b'SWAP', SWAP)
POP(R0)
Load_word(R1, 10)
Store_word(R0, 10)
PUSH(R1)
NEXT()


defcode(b'-', SUB)
POP(R0)
PEEK(R1)
Sub(R1, R1, R0)
POKE(R1)
NEXT()


defcode(b'*', MUL)
POP(R0)
PEEK(R1)
Mul(R1, R1, R0)
POKE(R1)
NEXT()


defcode(b'=', EQU)
POP(R0)
POP(R1)
Sub(R1, R1, R0)
Mov(R0, 0, u=True, v=True)  # Get flags, c register is ignored.
Asr_imm(R0, R0, 30)  # Z is the 31st bit, penultimate from the MSB.
And_imm(R0, R0, 1)  # Mask out N flag.
PUSH(R0)
NEXT()


defcode(b'>=', GTE)
POP(R0)
POP(R1)
Sub(R1, R1, R0)
GE_imm(_GTE_True)
Mov_imm(R0, 0)
T_imm(_GTE_fin)
label(_GTE_True)
Mov_imm(R0, 1)
label(_GTE_fin)
PUSH(R0)
NEXT()


defcode(b'1+', INCR)
PEEK(R0)
Add_imm(R0, R0, 1)
POKE(R0)
NEXT()


defcode(b'1-', DECR)
PEEK(R0)
Sub_imm(R0, R0, 1)
POKE(R0)
NEXT()


defcode(b'+!', ADDSTORE)
POP(R0)  # addr
POP(R1)  # "the amount to add"
Load_word(R2, R0)
Add(R2, R2, R1)
Store_word(R2, R0)
NEXT()


##  ___   _____
## |_ _| / / _ \
##  | | / / (_) |
## |___/_/ \___/

defcode(b'KEY', KEY)
busywait_on_serial_ready()
Load_word(R0, R1, negative_offset_20(-4))  # serial port is 4 bytes lower.
PUSH(R0)
NEXT()

defcode(b'EMIT', EMIT)
POP(R0)
busywait_on_serial_ready()
Store_word(R0, R1, negative_offset_20(-4))  # serial port is 4 bytes lower.
NEXT()


##     _  _______   __
##    | |/ / __\ \ / /
##    | ' <| _| \ V /
##  __|_|\_\___| |_|
## |___|
#
# Subroutine to busywait on serial port status.
# Sets R1 to point to SERIAL_STATUS i/o port.
# Clobbers R2.

label(_KEY)
move_immediate_word_to_register(R1, SERIAL_STATUS)
Load_word(R2, R1)
EQ_imm(negative_offset_24(-8))  # if R2==0 repeat
# Note that the machine will have incremented the PC
# by four already, so we jump back two words (-8 bytes)
# to reach the Load_word() instruction.  (I could use
# another label, but this seems sufficient.)
T(15)  # return


##     _    _           _
##    | |__| |__ _ _ _ | |__
##    | '_ \ / _` | ' \| / /
##  __|_.__/_\__,_|_||_|_\_\
## |___|
#
# Subroutine to check for blank space.
# Expects a char in R0.
# Clobbers R2.
# Sets Z flag to indicate blank space.
#       9,   10,     11,     12,   13,  32
#    '\t', '\n', '\x0b', '\x0c', '\r', ' '
# Check for most common (' ' and '\n') first.

label(_blank)
Sub_imm(R2, R0, 32)  # Is it a space char?
EQ(15)
Sub_imm(R2, R0, 10)  # Is it a newline char?
EQ(15)
Sub_imm(R2, R0, 9)  # Is it a tab char?
EQ(15)
Sub_imm(R2, R0, 11)  # Is it a '\x0b' char?
EQ(15)
Sub_imm(R2, R0, 12)  # Is it a '\x0c' char?
EQ(15)
Sub_imm(R2, R0, 13)  # Is it a carriage return char?
T(15)  # return

##        _   _                                   _
##     __| |_(_)_ __   __ ___ _ __  _ __  ___ _ _| |_
##    (_-< / / | '_ \ / _/ _ \ '  \| '  \/ -_) ' \  _|
##  __/__/_\_\_| .__/_\__\___/_|_|_|_|_|_\___|_||_\__|
## |___|       |_| |___|
#
# Subroutine to skip line ('\...') comments.
# Expects a char in R0,
# and for R1 to already be set to SERIAL_STATUS.
# Clobbers R2.

label(_skip_comment)
Sub_imm(R2, R0, ord('\\'))  # Is it a '\' char?
NE(15)                      # It's not a '\' char, return.
# Consume chars until the next newline.
label(_skip_cmt_loop)   # repeat...
Load_word(R2, R1)           # Get the serial port status.
EQ_imm(_skip_cmt_loop)      # until serial port status != 0
Load_word(R0, R1, negative_offset_20(-4))  # serial port is 4 bytes lower.
Sub_imm(R2, R0, ord('\n'))  # Is it a newline char?
EQ(15)  # We have reached the end of the line, return.
T_imm(_skip_cmt_loop)   # ...until newline.


## __      _____  ___ ___
## \ \    / / _ \| _ \   \
##  \ \/\/ / (_) |   / |) |
##   \_/\_/ \___/|_|_\___/
#
# This version does NOT push the length nor the address.
# The address is fixed at WORD_BUFFER and the length is
# put into the first byte.

label(WORD_BUFFER, reserves=32)

defcode(b'WORD', WORD)

label(_word_key)  # <=================================( _word_key )======

# Get a byte from the serial port.
busywait_on_serial_ready()
Load_word(R0, R1, negative_offset_20(-4))  # serial port is 4 bytes lower.

Mov_imm(R2, _skip_comment)  # Skip line comments.
T_link(R2)

Mov_imm(R1, _blank)  # Is it a space char?
T_link(R1)
EQ_imm(_word_key)  # then get another char

# Set up buffer and counter.
Mov_imm(word_pointer, WORD_BUFFER)
Mov_imm(word_counter, 0)
Store_word(word_counter, word_pointer)  # Zero out the first word of WORD_BUFFER.
# We use it for FIND so any leftover chars will mess it up for short words (of
# length 1 or 2.)
Add_imm(word_pointer, word_pointer, 1)  # Leave a byte for the length.

# Have we overflowed the buffer yet?
label(_find_length)  # <==============================( _find_length )===
Sub_imm(R2, word_counter, 32)
EQ_imm(_word_key)  # try again.

# Save the char to the buffer
Store_byte(R0, word_pointer)
Add_imm(word_pointer, word_pointer, 1)
Add_imm(word_counter, word_counter, 1)

# Get the next character, breaking if it's a space.
busywait_on_serial_ready()
Load_word(R0, R1, negative_offset_20(-4))  # serial port is 4 bytes lower.

# Is it a space char?
Mov_imm(R1, _blank)
T_link(R1)
NE_imm(_find_length)  # No, keep getting chars to the buffer

# Otherwise, if it's a space, save the length and return.
Mov_imm(word_pointer, WORD_BUFFER)
Store_byte(word_counter, word_pointer)
NEXT()


##  ___ ___ _  _ ___
## | __|_ _| \| |   \
## | _| | || .` | |) |
## |_| |___|_|\_|___/

defcode(b'FIND', FIND)

# Make sure the word_pointer points to the WORD_BUFFER.
# (Reserve this register?)
Mov_imm(word_pointer, WORD_BUFFER)
# Reuse the counter to get first word of the name.
Load_word(word_counter, word_pointer)
# Allow for the HIDDEN bit (but not IMMEDIATE bit) in the flags
# to hide a word from FIND.
move_immediate_word_to_register(R2, FIND_MASK)

Mov_imm(R0, LATEST_var)
Load_word(R0, R0)          # Point R0 to latest word's LFA.
label(_FIND_1)  # <==============================( _FIND_1 )===
Load_word(R1, R0, 4)       # load a word of the name field.
And(R1, R1, R2)            # Clear the IMMEDIATE flag, if any.
Sub(R1, R1, word_counter)  # Compare.
EQ_imm(_found)             # If this is the word...
# The two word are the same: same count and same first three letters.
# That's plenty for now.  (I believe I've heard of Chuck Moore using
# this heuristic.)

# If it's not a match...
Load_word(R0, R0)  # Load the address of the next link field into R0
NE_imm(_FIND_1)  # Check the next word.
# We know R0 is 0x00000000, so push it to signal failure.

label(_found)  # <================================( _found )===
PUSH(R0)
NEXT()


##  _  _ _   _ __  __ ___ ___ ___
## | \| | | | |  \/  | _ ) __| _ \
## | .` | |_| | |\/| | _ \ _||   /
## |_|\_|\___/|_|  |_|___/___|_|_\
#
# Parse the number in the WORD_BUFFER.
# To keep things simple, numbers are in hexidecimal only (no BASE)
# and must begin with a '$' and {abcdef} must be lowercase.
# No negative literals (subtract from zero to get negative numbers.)

defcode(b'NUMBER', NUMBER)

## ASCII ch
##    48 0
##    49 1
##    50 2
##    51 3
##    52 4
##    53 5
##    54 6
##    55 7
##    56 8
##    57 9
#
##    97 a
##    98 b
##    99 c
##   100 d
##   101 e
##   102 f

Mov_imm(word_pointer, WORD_BUFFER)
Load_byte(word_counter, word_pointer)
Mov_imm(R2, 0)  # use R2 as the accumulator for the number's value

Add_imm(word_pointer, word_pointer, 1)  # Point to first char.
Load_byte(R0, word_pointer)  # Load it.
Sub_imm(R0, R0, ord('$'))  # Is it a '$'?
NE_imm(_NUM_fin)

# It is a '$', let's parse a hex lit.
Sub_imm(word_counter, word_counter, 1)  # we have parsed one '$' char.

label(_NUM_hex)  # <============================( _NUM_hex )===
Add_imm(word_pointer, word_pointer, 1)  # Point to next char.
Load_byte(R0, word_pointer)  # Load it.

Sub_imm(R0, R0, ord('0'))
LT_imm(_NUM_fin)  # Is its ASCII value lower than '0'?

Sub_imm(R1, R0, 9)  # Is it 0-9?
LE_imm(_NUM_add)  # It is!

# It is not 0-9, but is it a-f?
# We have already subtracted 48 from it, so if it was 'a' (97)
# it would now be '1' (49 = 97 - 48).  We want to know if it's
# between 49 and 54 inclusive.  ('f' (102) -> '6' (54 = 102 - 48).)
Sub_imm(R0, R0, 49)  # so now '1'..'6' -> 0..5
LT_imm(_NUM_fin)  # Its ASCII value is less than 'a', nope out.

# It is >='a' but is it <='f'?
Sub_imm(R1, R0, 5)  # Is it a-f?
GT_imm(_NUM_fin)  # nope, nope out
# It is a-f.
Add_imm(R0, R0, 10)  # 0..5 -> 10..15

label(_NUM_add)  # <============================( _NUM_add )===
Add( R2, R2, R0)  # Add it to the accumulator.

Sub_imm(word_counter, word_counter, 1)  # we have parsed a digit char.
NE_imm(_NUM_foo)  # More digits? Keep going.
# That was all the digits, done.

label(_NUM_fin)  # <============================( _NUM_fin )===
PUSH(R2)
PUSH(word_counter)
NEXT()

label(_NUM_foo)  # <============================( _NUM_foo )===
Lsl_imm(R2, R2, 4)  # accumulator *= 16
T_imm(_NUM_hex)  # Go get the next digit.


##   ___ ___ ___   _ _____ ___
##  / __| _ \ __| /_\_   _| __|
## | (__|   / _| / _ \| | | _|
##  \___|_|_\___/_/ \_\_| |___|

defcode(b'CREATE', CREATE)

# Link field.
Mov_imm(R0, HERE__var)  # R0 <- &HERE
Load_word(R0, R0)       # R0 <- ram[HERE]

Mov_imm(R1, LATEST_var)  # R1 <- &LATEST
Load_word(R2, R1)        # R2 <- ram[LATEST]

Store_word(R2, R0)  # value of LATEST -> ram[HERE]
Store_word(R0, R1)  # value of HERE (now LFA for new word) -> ram[LATEST]

Add_imm(R0, R0, 4)  # HERE += 4

# Name field.
Mov_imm(word_pointer, WORD_BUFFER)
# When I decided that words would only store 4 bytes of name field
# I forgot to remove the code here that copied the whole name from
# the WORD_BUFFER, which resulted in a bug when I tried to define
# THEN in Forth.
##Load_byte(word_counter, word_pointer)
##And_imm(word_counter, word_counter, F_LENMASK)
##Asr_imm(word_counter, word_counter, 2)  # How many words?
##label(_CREATE_loop)  # <========================( _CREATE_loop )===

Load_word(R1, word_pointer)  # Get the word from WORD_BUFFER.
Store_word(R1, R0)  # Store word to HERE.
Add_imm(R0, R0, 4)  # HERE += 4

##Sub_imm(word_counter, word_counter, 1)
##LT_imm(_CREATE_fin)  # There are no more words.
### There are more words.
##Add_imm(word_pointer, word_pointer, 4)
##T_imm(_CREATE_loop)
##
##label(_CREATE_fin)  # <==========================( _CREATE_fin )===

# Update HERE.
Mov_imm(R1, HERE__var)  # R1 <- &HERE
Store_word(R0, R1)      # value of HERE -> ram[HERE]
NEXT()


##  ___         _
## / __|_  _ __| |_ ___ _ __
## \__ \ || (_-<  _/ -_) '  \
## |___/\_, /__/\__\___|_|_|_|
## __   |__/      _      _    _
## \ \ / /_ _ _ _(_)__ _| |__| |___ ___
##  \ V / _` | '_| / _` | '_ \ / -_|_-<
##   \_/\__,_|_| |_\__,_|_.__/_\___/__/

defvar(b'HERE', HERE_, initial=END)
defvar(b'LATEST', LATEST, initial=DUP_dfa)
defvar(b'STATE', STATE)

defconst(b'DOCOL', __DOCOL, DOCOL)


##   ___ ___  __  __ __  __   _
##  / __/ _ \|  \/  |  \/  | /_\
## | (_| (_) | |\/| | |\/| |/ _ \
##  \___\___/|_|  |_|_|  |_/_/ \_\

defcode(b',', COMMA)
POP(R2)
Mov_imm(R1, _COMMA)
T_link(R1)
NEXT()

# Subroutine to store a value to HERE and
# increment HERE (by four bytes to the next word.)
# Expects the value in R2.
# Clobbers R0 and R1.
# Used in _INTERP.
label(_COMMA)
Mov_imm(R0, HERE__var)  # R0 <- HERE__var
Load_word(R1, R0)       # HERE <- ram[HERE__var]
Store_word(R2, R1)      # R2 -> ram[HERE]
Add_imm(R1, R1, 4)      # HERE += 4
Store_word(R1, R0)      # HERE -> ram[HERE__var]
T(15)  # return


##  __   __       __
## | _| / _|___  |_ |
## | |  > _|_ _|  | |
## | |  \_____|   | |
## |__|          |__|
#
# Switch off ('[' executing)
#     and on (']' compiling)
# the STATE variable.

defcode(b'[', LBRAC, F_IMMED)
Mov_imm(R0, STATE_var)
Mov_imm(R1, 0)
Store_word(R1, R0)
NEXT()

defcode(b']', RBRAC)
Mov_imm(R0, STATE_var)
Mov_imm(R1, 1)
Store_word(R1, R0)
NEXT()


# If COLON and SEMICOLON were defined in Forth
# they might look like this:
#
# : : WORD CREATE LIT DOCOL , LATEST @ HIDDEN ] ;
# : ;             LIT EXIT  , LATEST @ HIDDEN [ ;
#                 ^^^^^^^^^^^ ^^^^^^^^^^^^^^^ ^
#                      |             |        |
#                 Store a CFA        |        |
#                                    |        |
#         Toggle hidden bit on current word.  |
#                                             |
#                    Switch on/off compiling mode.

##   ___ ___  _    ___  _  _
##  / __/ _ \| |  / _ \| \| |
## | (_| (_) | |_| (_) | .` |
##  \___\___/|____\___/|_|\_|

defword(b':', COLON)
dw(WORD)  # "Get the name of the new word"
dw(CREATE)  # "CREATE the dictionary entry / header"
dw(LIT)  # "Append DOCOL  (the codeword)."
dw(DOCOL)
dw(COMMA)
dw(LATEST)  # "Make the word hidden (see below for definition)."
dw(FETCH)
dw(HIDDEN)
dw(RBRAC)  # "Go into compile mode."
dw(EXIT)  # "Return from the function."


##  ___ ___ __  __ ___ ___ ___  _    ___  _  _
## / __| __|  \/  |_ _/ __/ _ \| |  / _ \| \| |
## \__ \ _|| |\/| || | (_| (_) | |_| (_) | .` |
## |___/___|_|  |_|___\___\___/|____\___/|_|\_|

defword(b';', SEMICOLON, F_IMMED)
dw(LIT)  # "Append EXIT (so the word will return)."
dw(EXIT)
dw(COMMA)
dw(LATEST)  # "Toggle hidden flag -- unhide the word (see below for definition)."
dw(FETCH)
dw(HIDDEN)
dw(LBRAC)  # "Go back to IMMEDIATE mode."
dw(EXIT)  # "Return from the function."


##  ___ __  __ __  __ ___ ___ ___   _ _____ ___
## |_ _|  \/  |  \/  | __|   \_ _| /_\_   _| __|
##  | || |\/| | |\/| | _|| |) | | / _ \| | | _|
## |___|_|  |_|_|  |_|___|___/___/_/ \_\_| |___|

defcode(b'IMMEDIATE', IMMEDIATE, F_IMMED)
Mov_imm(R0, LATEST_var)  # R0 <- &LATEST
Load_word(R1, R0)        # R1 <- ram[LATEST]
Add_imm(R1, R1, 4)       # "Point to name/flags byte."
Load_word(R0, R1)
Xor_imm(R0, R0, F_IMMED) # Toggle IMMEDIATE bit.
Store_word(R0, R1)
NEXT()


##  _  _ ___ ___  ___  ___ _  _
## | || |_ _|   \|   \| __| \| |
## | __ || || |) | |) | _|| .` |
## |_||_|___|___/|___/|___|_|\_|

defcode(b'HIDDEN', HIDDEN)
POP(R1)  # LFA is on the stack.
Add_imm(R1, R1, 4)  # "Point to name/flags byte."
Load_word(R0, R1)
Xor_imm(R0, R0, F_HIDDEN)  # "Toggle the HIDDEN bit."
Store_word(R0, R1)
NEXT()


##  _    _______ ___ ___ _  ____
## ( )  / /_   _|_ _/ __| |/ /\ \
## |/  | |  | |  | | (__| ' <  | |
##     | |  |_| |___\___|_|\_\ | |
##      \_\                   /_/
#
# Jones says of this implementation:
#
# > This definition of ' uses a cheat which I copied from buzzard92.  As a result it only works in
# > compiled code.  It is possible to write a version of ' based on WORD, FIND, >CFA which works in
# > immediate mode too.
#
# I just noticed, isn't this just LIT?

defcode(b"'", TICK)
Load_word(R0, IP)   # Get the address of the next codeword.
Add_imm(IP, IP, 4)  # Skip it.
PUSH(R0)
NEXT()


##  ___ ___    _   _  _  ___ _  _
## | _ ) _ \  /_\ | \| |/ __| || |
## | _ \   / / _ \| .` | (__| __ |
## |___/_|_\/_/ \_\_|\_|\___|_||_|

defcode(b'BRANCH', BRANCH)
Load_word(R0, IP)  # Get the offset.
# TODO: check for alignment?  make offset count words not bytes?
Add(IP, IP, R0)    # IP += offset
NEXT()


##  _______ ___    _   _  _  ___ _  _
## |_  / _ ) _ \  /_\ | \| |/ __| || |
##  / /| _ \   / / _ \| .` | (__| __ |
## /___|___/_|_\/_/ \_\_|\_|\___|_||_|

defcode(b'0BRANCH', ZBRANCH)
POP(R0)
Add_imm(R0, R0, 0)  # Set condition flags.
EQ_imm(BRANCH + 4)  # Zero? Delegate to BRANCH.
Add_imm(IP, IP, 4)  # Non-zero? Skip offset.
NEXT()


##  ___ ___ _____ ___ _  _
## | __| __|_   _/ __| || |
## | _|| _|  | || (__| __ |
## |_| |___| |_| \___|_||_|

defcode(b'@', FETCH)
PEEK(R0)
Load_word(R0, R0)
POKE(R0)
NEXT()


##  ___ _____ ___  ___ ___
## / __|_   _/ _ \| _ \ __|
## \__ \ | || (_) |   / _|
## |___/ |_| \___/|_|_\___|

defcode(b'!', STORE)
POP(R0)
POP(R1)
Store_word(R1, R0)
NEXT()



##    _ _  ___
##  _| | ||__ \
## |_  .  _|/_/
## |_     _(_)
##   |_|_|
#
# Is the most recently parsed word (probably) a numeric literal?
# (This check does not affect the word buffer, unlike NUMBER.)
# Leaves a value on the stack: 0 for true or non-0 for false.

defcode(b'#?', IS_NUMBER)
Mov_imm(word_pointer, WORD_BUFFER)
Load_byte(R0, word_pointer, 1)  # Load first char of word.
Sub_imm(R0, R0, ord('$'))  # Is it a '$'?
PUSH(R0)  # Let the result be the result:
NEXT()    # 0 -> true / != 0 -> false


##  ___ _  _ _____ ___ ___ ___ ___ ___ _____
## |_ _| \| |_   _| __| _ \ _ \ _ \ __|_   _|
##  | || .` | | | | _||   /  _/   / _|  | |
## |___|_|\_| |_| |___|_|_\_| |_|_\___| |_|

defword(b'INTERPRET', INTERPRET)
dw(WORD)
dw(IS_NUMBER)
dw(ZBRANCH)
dw(s_to_u_32(4 * 7))  # It could be a number...

# It's not a number but it might be a word.
dw(FIND)
dw(DUP)
dw(ZBRANCH)  # Zero means it wasn't in the dictionary,
dw(s_to_u_32(4 * 7))

# It's in the dictionary and its LFA is in TOS
dw(_INTERP)
dw(EXIT)

# It could be a number, so let's try that...
dw(NUMBER)
dw(DUP)
dw(ZBRANCH)  # No chars left?  It is a number!
dw(s_to_u_32(4 * 2))

# It wasn't a number, even though it started with '$'
##dw(ERROR)
dw(EXIT)

# It IS a number.  DROP the word count (which is zero.)
dw(DROP)
# If we are interpreting, we are done, the number is on
# the stack already.  If we are compiling we need to write
# the address of the codeword of LIT, then the value itself.
dw(STATE)
dw(FETCH)
dw(ZBRANCH)  #  STATE = 0 -> interpreting.
# Just leave the number itself on the stack.
dw(s_to_u_32(4 * 5))  # to EXIT

# we are compiling
dw(LIT)
dw(LIT)
dw(COMMA)  # write the address of the codeword of LIT
dw(COMMA)  # then the value itself.

dw(EXIT)


##     ___ _  _ _____ ___ ___ ___
##    |_ _| \| |_   _| __| _ \ _ \
##     | || .` | | | | _||   /  _/
##  __|___|_|\_| |_| |___|_|_\_|
## |___|
defcode(b'_INTERP', _INTERP, F_HIDDEN)
# Do the thing with the LFA in TOS.
POP(R2)

# If we are interpreting, or the word is IMMEDIATE, execute it.
Mov_imm(R0, STATE_var)  # R0 <- &STATE
Load_word(R0, R0)  # R0 <- ram[STATE]
EQ_imm(_intrp_exe)  # STATE = 0 -> interpreting.
Load_word(R0, R2, 4)  # R0 <- Name field
And_imm(R0, R0, F_IMMED)
NE_imm(_intrp_exe)  # word is IMMEDIATE.

# We are compiling and the word is not immediate.
Add_imm(R2, R2, 8)  # Point from LFA to codeword.
Mov_imm(R1, _COMMA)  # Call comma to store it and increment HERE.
T_link(R1)
NEXT()

label(_intrp_exe)  # Execute the word.
Add_imm(R2, R2, 8)  # Point to the codeword
Load_word(R0, R2)  # Get the address to which its codeword points...
Mov(next_function, R2)  # DOCOL depends on this.
T(R0)  # and jump to it.


##  ___ ___ ___ ___ _      ___   __
## |   \_ _/ __| _ \ |    /_\ \ / /
## | |) | |\__ \  _/ |__ / _ \ V /
## |___/___|___/_| |____/_/ \_\_|

DISPLAY_START = 0xE7F00
DISPLAY_LENGTH = 0x18000
FONT_SIZE = 312 * 4  # 312 words of font data.
R7, R8 = 7, 8  # We use a couple of extra registers.


##             _
##  _ __  __ _(_)
## | '_ \/ _` | |
## | .__/\__,_|_|
## |_|
#
# "pai"nt the font data to the screen so we can see it.

defcode(b'pai', PAI)
move_immediate_word_to_register(R0, DISPLAY_START)
move_immediate_word_to_register(R1, DISPLAY_LENGTH)
move_immediate_word_to_register(R8, 0xffffffff)
Add(R1, R1, R0)
Sub_imm(R0, R0, 312 * 4)  # 312 words in font data.
Mov_imm(R2, 13 * 24)

label(_pai_loop)  # <-------------
Load_word(R7, R0)
Xor(R7, R7, R8)  #  Reverse video.
Store_word(R7, R1)
Add_imm(R0, R0, 4)
Sub_imm(R1, R1, 128)
Sub_imm(R2, R2, 1)
NE_imm(_pai_loop)
NEXT()


##             _     _        _
##  _ __  __ _(_)_ _| |_   __| |_  __ _ _ _
## | '_ \/ _` | | ' \  _| / _| ' \/ _` | '_|
## | .__/\__,_|_|_||_\__|_\__|_||_\__,_|_|
## |_|                 |___|
#
# (y x chr -- )
# Paint a char onto the screen.
# The coordinates are in character "space":
# 0, 0 is the upper left corner,
# there are 1024/8 = 128 characters per line
# and 768/13 ~= 59 lines.
# So 0 <= x < 128 and 0 <= y < 59 (not checked.)
# The chr value should be ASCII.  (The font I'm
# using includes Unicode characters but I
# haven't worked out how I want to use them just
# yet.  I'm thinking about a 32-bit parallel port?
# But then how to represent things like mode keys?
# Press/release events?  Maybe emulating the PS/2
# isn't such a gnarly idea?)

defcode(b'paint_char', PAINT_CHAR)

move_immediate_word_to_register(R0, DISPLAY_START - 312 * 4)
# DISPLAY_START - 312 words in font data * 4 bytes/word.
# R0 points to start of font data.  0x000e7a20

POP(R1)  # chr in R1
Sub_imm(R1, R1, ord('!'))  # R1 counts byte offset of char.

Asr_imm(R2, R1, 2)     # R2 = R1 / 4  Trim the two least bits.
Mul_imm(R2, R2, 52)    # R2 *= 13 words/char * 4 bytes/word.
Add(R0, R0, R2)        # Point R0 to char's first word in font.
And_imm(R1, R1, 0b11)  # Which byte in the word?
Add(R0, R0, R1)        # Point R0 to char's first byte in font.

POP(R1)  # x
move_immediate_word_to_register(R2, DISPLAY_START)
Add(R1, R1, R2)     # R1 = x + DISPLAY_START
Mov_imm(R7, 767)    # Display width - 1 in pixels. (TODO don't hardcod3 this.)
POP(R2)             # R2 = y in lines
Mul_imm(R2, R2, 13) # R2 = y in px  (13px/char height)
Sub(R2, R7, R2)     # R2 = 768 - 1 - y
Lsl_imm(R2, R2, 7)  # R2 = (768 - 1 - y) * 128 bytes per line.
Add(R1, R1, R2)     # R1 = (768 - 1 - y) * 128 + x + DISPLAY_START

# So at this point, if I got everything above right,
# R0 points to start of char's first byte in font data.
# R1 points to the first destination byte in screen RAM.

Mov_imm(R2, 13)  # Counter
##move_immediate_word_to_register(R8, 0xffffffff)
label(_pchr_loop)  # <-------------
Load_byte(R7, R0)
##Xor(R7, R7, R8)  #  Reverse video.
Store_byte(R7, R1)
Add_imm(R0, R0, 4)
Sub_imm(R1, R1, 128)
Sub_imm(R2, R2, 1)
NE_imm(_pchr_loop)
NEXT()


defcode(b'TRAP', TRAP)
NEXT()




# Rather than continue updating (or forgetting to update) LATEST
# just put DUP at the end.

##  ___  _   _ ___
## |   \| | | | _ \
## | |) | |_| |  _/
## |___/ \___/|_|

defcode(b'DUP', DUP)
PEEK(R0)
PUSH(R0)
NEXT()

label(END)
