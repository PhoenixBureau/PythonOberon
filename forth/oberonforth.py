from oberon.util import s_to_u_32

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
F_IMMED = 0x80
F_HIDDEN = 0x20
F_LENMASK = 0x1f

# I/O
SERIAL_PORT = s_to_u_32(-56)  # io_ports[8]
SERIAL_STATUS = s_to_u_32(-52)  # io_ports[12]

# Dictionary 
LINK = 0


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
    global LINK
    dw(LINK)
    LINK = HERE() - 4
    name_len = len(name)
    assert name_len < 32, repr(name)
    name_bytes = [name_len]
    name_bytes.extend(name)  # Converts bytes to [int].
    while len(name_bytes) % 4: name_bytes.append(0)
    for i in range(0, len(name_bytes), 4):
        a, b, c, d = name_bytes[i:i+4]
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
    Mov_imm(R0, LABEL_var)
    PUSH(R0)
    NEXT()
    label(LABEL_var)
    dw(initial)


def HIGH(i):
    return (i >> 16) & 0xFFFF


def LOW(i):
    return i & 0xFFFF


def move_immediate_word_to_register(reg, word):
    Mov_imm(reg, HIGH(word), u=1)
    Ior_imm(reg, reg, LOW(word))


def busywait_on_serial_ready():
    move_immediate_word_to_register(R1, SERIAL_STATUS)
    Load_word(R2, R1, 0)
    EQ_imm(negative_offset_24(-8))  # if R2==0 repeat


negative_offset_24 = lambda n: s_to_u_32(n) & 0xffffff
negative_offset_20 = lambda n: s_to_u_32(n) & 0x0fffff


T_imm(main)
label(_reserved, reserves=36)

label(DOCOL)
PUSHRSP(IP)
# Point from the codeword to the first data word.
Add_imm(IP, next_function, 4)
NEXT()

label(main)
Mov_imm(Dstack, DATA_STACK)
Mov_imm(Rstack, RETURN_STACK)
Mov_imm(IP, cold_start)
Mov_imm(R1, 38)  # ASCII '&'
PUSH(R1)
NEXT()

label(cold_start)
dw(EMIT)
#dw(QUIT)  # IP starts pointing here so this RAM address must
          # contain the address of the codeword of QUIT.

defcode(b'DROP', DROP)
Add_imm(Dstack, Dstack, 4)  # drop top of stack
NEXT()

defcode(b'EXIT', EXIT)
POPRSP(IP)
NEXT()

defcode(b'LIT', LIT)
Load_word(R0, IP)
Add_imm(IP, IP, 4)                  # IP += 4
PUSH(R0)
NEXT()

defcode(b'KEY', KEY)
##busywait_on_serial_ready()
Mov_imm(R1, _KEY)
T_link(R1)
Load_word(R0, R1, negative_offset_20(-4))  # serial port is 4 bytes lower.
PUSH(R0)
NEXT()

defcode(b'EMIT', EMIT)
POP(R0)
##busywait_on_serial_ready()
Mov_imm(R1, _KEY)
T_link(R1)
Store_word(R0, R1, negative_offset_20(-4))  # serial port is 4 bytes lower.
NEXT()

defcode(b'SWAP', SWAP)
POP(R0)
Load_word(1, 10)
Store_word(0, 10)
PUSH(R1)
NEXT()

defvar(b'LATEST', LATEST, initial=LINK)
# Later link to actual last value/label.


label(_KEY)
# subroutine to busywait on serial port status.
# Sets R1 to point to SERIAL_STATUS i/o port.
# Clobbers R2.
move_immediate_word_to_register(R1, SERIAL_STATUS)
Load_word(R2, R1, 0)
EQ_imm(negative_offset_24(-8))  # if R2==0 repeat
T(15)  # return


label(WORD_BUFFER, reserves=32)

defcode(b'WORD', WORD)

# call _KEY
Mov_imm(R1, _KEY)
label(_word_key)
T_link(R1)

# Get a byte from the serial port.
Load_word(R0, R1, negative_offset_20(-4))  # serial port is 4 bytes lower.

# Is it a space char?
Sub_imm(R2, R0, ord(' '))
EQ_imm(_word_key)  # then get another char

# Set up buffer and counter.
label(_a_key)
Mov_imm(word_pointer, WORD_BUFFER)
Mov_imm(word_counter, 0)

# I think we're going to want to put the length in the first
# byte of the buffer to make word-by-word comparison easier?
# (For finding words in the dictionary.)

# Have we overflowed the buffer yet?
label(_find_length)
Sub_imm(R2, word_counter, 32)
EQ_imm(_a_key)  # then reset word and try again.

# Save the char to the buffer
Store_byte(R0, word_pointer)
Add_imm(word_pointer, word_pointer, 1)
Add_imm(word_counter, word_counter, 1)

# Get the next character, breaking if it's a space.
T_link(R1)  # Still points to _KEY
Load_word(R0, R1, negative_offset_20(-4))  # serial port is 4 bytes lower.
# Is it a space char?
Sub_imm(R2, R0, ord(' '))
NE_imm(_find_length)  # No, keep getting chars to the buffer

# Otherwise, if it's a space, push the length and return.
PUSH(word_counter)
NEXT()


label(QUIT)




















