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
'''
# The chip uses two's complement.
from oberon.util import s_to_u_32


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
    Load_word(next_function, IP)        # next_function <- RAM[IP]
    Load_word(codeword, next_function)  # codeword <- RAM[next_function]
    Add_imm(IP, IP, 4)                  # IP += 4
    T(codeword)                         # PC <- RAM[codeword]


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
    PUSH(R0)
    NEXT()
    # Reserve a word of RAM for the variable.
    label(LABEL_var)
    dw(initial)


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


# FIGlet SaaS:
# http://www.patorjk.com/software/taag/


##  _              _
## | |__  ___ __ _(_)_ _
## | '_ \/ -_) _` | | ' \
## |_.__/\___\__, |_|_||_|
##           |___/
T_imm(main)
label(_reserved, reserves=36)


##  ___   ___   ___ ___  _
## |   \ / _ \ / __/ _ \| |
## | |) | (_) | (_| (_) | |__
## |___/ \___/ \___\___/|____|

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
##Mov_imm(R1, 38)  # push ASCII '&' onto stack
##PUSH(R1)
NEXT()


##         _    _      _            _
##  __ ___| |__| |  __| |_ __ _ _ _| |_
## / _/ _ \ / _` | (_-<  _/ _` | '_|  _|
## \__\___/_\__,_|_/__/\__\__,_|_|  \__|
##              |___|
label(cold_start)
dw(REPL)
#dw(QUIT)  # IP starts pointing here so this RAM address must
          # contain the address of the codeword of QUIT.


##                    _
## __ __ _____ _ _ __| |___
## \ V  V / _ \ '_/ _` (_-<
##  \_/\_/\___/_| \__,_/__/

defword(b'REPL', REPL)
dw(WORD)
#dw(FIND)
dw(CREATE)
dw(BRANCH)
dw(s_to_u_32(-12))


defcode(b'DROP', DROP)
Add_imm(Dstack, Dstack, 4)  # drop top of stack
NEXT()


defcode(b'EXIT', EXIT)
POPRSP(IP)  # Restore previous IP from the Return Stack.
NEXT()


defcode(b'LIT', LIT)
Load_word(R0, IP)  # Don't run the next word, load it,
PUSH(R0)  # push the value,
Add_imm(IP, IP, 4)  # then skip it and run the word after it (EXIT).
NEXT()


defcode(b'SWAP', SWAP)
POP(R0)
Load_word(1, 10)
Store_word(0, 10)
PUSH(R1)
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
# subroutine to busywait on serial port status.
# Sets R1 to point to SERIAL_STATUS i/o port.
# Clobbers R2.

label(_KEY)
move_immediate_word_to_register(R1, SERIAL_STATUS)
Load_word(R2, R1, 0)
EQ_imm(negative_offset_24(-8))  # if R2==0 repeat
# Note that the machine will have incremented the PC
# by four already, so we jump back two words (-8 bytes)
# to reach the Load_word() instruction.  (I could use
# another label, but this seems sufficient.)
T(15)  # return


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

# Is it a space char?
Sub_imm(R2, R0, ord(' '))
EQ_imm(_word_key)  # then get another char

# Set up buffer and counter.
Mov_imm(word_pointer, WORD_BUFFER + 1)  # Leave a byte for the length.
Mov_imm(word_counter, 0)

# I think we're going to want to put the length in the first
# byte of the buffer to make word-by-word comparison easier?
# (For finding words in the dictionary.)

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
Sub_imm(R2, R0, ord(' '))
NE_imm(_find_length)  # No, keep getting chars to the buffer

# Otherwise, if it's a space, save the length and return.
# (WORD_BUFFER is a constant.)
Mov_imm(word_pointer, WORD_BUFFER)
Store_byte(word_counter, word_pointer)
NEXT()


##  ___ ___ _  _ ___
## | __|_ _| \| |   \
## | _| | || .` | |) |
## |_| |___|_|\_|___/

defcode(b'FIND', FIND)

# Load the LATEST var into a register.
Mov_imm(R0, LATEST_var)
EQ_imm(_end_of_dict)  # Null pointer (should never happen here, eh?)

label(_FIND_1)  # <==============================( _FIND_1 )===
Load_word(R1, R0)  # Load the address of the word's link field
Load_word(R0, R1, 4)  # load a word of the name field.

# Make sure the word_pointer points to the WORD_BUFFER.
Mov_imm(word_pointer, WORD_BUFFER)
# Reuse the counter to store parts of the name.
Load_word(word_counter, word_pointer)

Sub(R0, R0, word_counter)
NE_imm(_FIND_2)  # If these two words differ then load the next word.

# The two word are the same, same count, and same first three letters.
# That's plenty for now.
PUSH(R1)
NEXT()

label(_FIND_2)  # <==============================( _FIND_2 )===
Load_word(R0, R1)  # Load the next link field into R0
EQ_imm(_end_of_dict)  # Null pointer
T_imm(_FIND_1)  # Check the next word.

label(_end_of_dict)  # <==============================( _end_of_dict )===
# We know R0 is 0x00000000, so push it to signal failure.
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
Load_word(R0, R0)  # R0 <- ram[HERE]

Mov_imm(R1, LATEST_var)  # R1 <- &LATEST
Load_word(R1, R1)  # R1 <- ram[LATEST]
Store_word(R1, R0)  # value of LATEST -> ram[HERE]
Add_imm(R0, R0, 4)  # HERE += 4
# I think that's right...

# Name field.
Mov_imm(word_pointer, WORD_BUFFER)
Load_byte(word_counter, word_pointer)
And_imm(word_counter, word_counter, F_LENMASK)
Asr_imm(word_counter, word_counter, 2)  # How many words?

label(_CREATE_loop)  # <========================( _CREATE_loop )===

Load_word(R1, word_pointer)  # Get the word from WORD_BUFFER.
Store_word(R1, R0)  # Store word to HERE.
Add_imm(R0, R0, 4)  # HERE += 4
Sub_imm(word_counter, word_counter, 1)
LT_imm(_CREATE_fin)  # There are no more words.
# There are more words.
Add_imm(word_pointer, word_pointer, 4)
T_imm(_CREATE_loop)

label(_CREATE_fin)  # <==========================( _CREATE_fin )===
# Update HERE.
Mov_imm(R1, HERE__var)  # R1 <- &HERE
Store_word(R0, R1)
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
defvar(b'LATEST', LATEST, initial=FETCH_dfa)
defvar(b'STATE', STATE)


##   ___ ___  __  __ __  __   _
##  / __/ _ \|  \/  |  \/  | /_\
## | (_| (_) | |\/| | |\/| |/ _ \
##  \___\___/|_|  |_|_|  |_/_/ \_\

defcode(b',', COMMA, F_IMMED)
POP(R2)
Mov_imm(R1, _COMMA)
T_link(R1)
NEXT()

label(_COMMA)
Mov_imm(R0, HERE__var)  # R0 <- &HERE
Load_word(R1, R0)  # R1 <- ram[&HERE]
Store_word(R2, R1)  # R2 -> ram[HERE]
Add_imm(R1, R1, 4)
Store_word(R1, R0)  # R1+4 -> ram[&HERE]
T(15)  # return


##  __   __       __
## | _| / _|___  |_ |
## | |  > _|_ _|  | |
## | |  \_____|   | |
## |__|          |__|

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

label(END)


##  ___ __  __ __  __ ___ ___ ___   _ _____ ___
## |_ _|  \/  |  \/  | __|   \_ _| /_\_   _| __|
##  | || |\/| | |\/| | _|| |) | | / _ \| | | _|
## |___|_|  |_|_|  |_|___|___/___/_/ \_\_| |___|

defcode(b'IMMEDIATE', IMMEDIATE, F_IMMED)
Mov_imm(R0, LATEST_var)  # R0 <- &LATEST
Load_word(R1, R0)  # R1 <- ram[LATEST]
Add_imm(R1, R1, 4)  # "Point to name/flags byte."
Load_word(R0, R1)
Xor_imm(R0, R0, F_IMMED)
Store_word(R0, R1)
NEXT()


##  _  _ ___ ___  ___  ___ _  _
## | || |_ _|   \|   \| __| \| |
## | __ || || |) | |) | _|| .` |
## |_||_|___|___/|___/|___|_|\_|

defcode(b'HIDDEN', HIDDEN)
POP(R1)  # dfa OF A WORD IS ON THE STACK
Add_imm(R1, R1, 4)  # "Point to name/flags byte."
Load_word(R0, R1)  # "Toggle the HIDDEN bit."
Xor_imm(R0, R0, F_HIDDEN)
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

defcode(b"'", TICK)
Load_word(R0, IP)  # Get the address of the next codeword.
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
NE_imm(BRANCH + 4)  # Non-zero? BRANCH.
Add_imm(IP, IP, 4)  # Zero? Skip offset.
NEXT()


defcode(b'@', FETCH)
POP(R0)
Load_word(R0, R0)
PUSH(R0)
NEXT()









label(QUIT)
