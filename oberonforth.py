
##
## 284         The all-important i386 instruction is called LODSL (or in Intel manuals, LODSW).  It does
## 285         two things.  Firstly it reads the memory at %esi into the accumulator (%eax).  Secondly it
## 286         increments %esi by 4 bytes.  So after LODSL, the situation now looks like this:
##

# Put these anywhere...
DATA_STACK = 0x4000
RETURN_STACK = 0x6000

# Registers
next_function = 2
codeword = 3
IP = 14       # (%esi)
Dstack = 10
Rstack = 12
R0, R1 = 0, 1


def NEXT():
    Load_word(next_function, IP)        # next_function <- RAM[IP]
    Load_word(codeword, next_function)  # codeword <- RAM[next_function]
    Add_imm(IP, IP, 4)                  # IP += 4
    T(codeword)                         # PC <- RAM[codeword]


##
## 473 /* Macros to deal with the return stack. */
## 474         .macro PUSHRSP reg
## 475         lea -4(%ebp),%ebp       // push reg on to return stack
## 476         movl \reg,(%ebp)
## 477         .endm
## 478 
## 479         .macro POPRSP reg
## 480         mov (%ebp),\reg         // pop top of return stack to reg
## 481         lea 4(%ebp),%ebp
## 482         .endm
## 483 
##

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


T_imm(main)
label(_reserved, reserves=36)


##
## 498 /* DOCOL - the interpreter! */
## 499         .text
## 500         .align 4
## 501 DOCOL:
## 502         PUSHRSP %esi            // push %esi on to the return stack
## 503         addl $4,%eax            // %eax points to codeword, so make
## 504         movl %eax,%esi          // %esi point to first data word
## 505         NEXT
##

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

##
## 580         BUILT-IN WORDS ----------------------------------------------------------------------
## 581 
## 582         Remember our dictionary entries (headers)?  Let's bring those together with the codeword
## 583         and data words to see how : DOUBLE DUP + ; really looks in memory.
## 584 
## 585           pointer to previous word
## 586            ^
## 587            |
## 588         +--|------+---+---+---+---+---+---+---+---+------------+------------+------------+------------+
## 589         | LINK    | 6 | D | O | U | B | L | E | 0 | DOCOL      | DUP        | +          | EXIT       |
## 590         +---------+---+---+---+---+---+---+---+---+------------+--|---------+------------+------------+
## 591            ^       len                         pad  codeword      |
## 592            |                                                      V
## 593           LINK in next word                             points to codeword of DUP
## 594         
## 595         Initially we can't just write ": DOUBLE DUP + ;" (ie. that literal string) here because we
## 596         don't yet have anything to read the string, break it up at spaces, parse each word, etc. etc.
## 597         So instead we will have to define built-in words using the GNU assembler data constructors
## 598         (like .int, .byte, .string, .ascii and so on -- look them up in the gas info page if you are
## 599         unsure of them).
##


F_IMMED = 0x80
F_HIDDEN = 0x20
F_LENMASK = 0x1f


LINK = 0


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
        dw(a<<24 + b<<16 + c<<8 + d)
    label(LABEL)
    dw(DOCOL)


## Example:
##
##    defword(b'double', DOUBLE)
##    dw(DUP),
##    dw(PLUS),
##    dw(EXIT)

##
## 648         Similarly I want a way to write words written in assembly language.  There will be quite a few
## 649         of these to start with because, well, everything has to start in assembly before there's
## 650         enough "infrastructure" to be able to start writing FORTH words, but also I want to define
## 651         some common FORTH words in assembly language for speed, even though I could write them in FORTH.
## 652 
## 653         This is what DUP looks like in memory:
## 654 
## 655           pointer to previous word
## 656            ^
## 657            |
## 658         +--|------+---+---+---+---+------------+
## 659         | LINK    | 3 | D | U | P | code_DUP ---------------------> points to the assembly
## 660         +---------+---+---+---+---+------------+                    code used to write DUP,
## 661            ^       len              codeword                        which ends with NEXT.
## 662            |
## 663           LINK in next word
## 664 
## 665         Again, for brevity in writing the header I'm going to write an assembler macro called defcode.
## 666         As with defword above, don't worry about the complicated details of the macro.
##


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

