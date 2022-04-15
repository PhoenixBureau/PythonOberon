
# Put these anywhere...
DATA_STACK = 0x4000
RETURN_STACK = 0x6000

# Registers
R0, R1 = 0, 1
next_function = 2
codeword = 3
IP = 14
Dstack = 10
Rstack = 12

# Flags
F_IMMED = 0x80
F_HIDDEN = 0x20
F_LENMASK = 0x1f

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
    Store_word(Rstack, reg)     # reg -> RAM[Rstack]


def POPRSP(reg):
    '''pop top of return stack to reg'''
    Load_word(reg, Rstack)      # reg <- RAM[Rstack]
    Add_imm(Rstack, Rstack, 4)  # Rstack += 4


def PUSH(reg):
    '''push reg onto stack'''
    Sub_imm(Dstack, Dstack, 4)  # Dstack -= 4
    Store_word(Dstack, reg)     # reg -> RAM[Dstack]


def POP(reg):
    '''pop top of stack to reg'''
    Load_word(reg, Dstack)      # reg <- RAM[Dstack]
    Add_imm(Dstack, Dstack, 4)  # Dstack += 4


def defword(name, LABEL, flags=0):
    assert isinstance(name, bytes)
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
    dw(DOCOL)


def defcode(name, LABEL, flags=0):
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
    dw(HERE() + 4)  # codeword, points to ASM immediately following.


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
NEXT()

label(cold_start)
dw(QUIT)  # IP starts pointing here so this RAM address must
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


label(QUIT)
