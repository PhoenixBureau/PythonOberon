from oberon.util import bint, signed_int_to_python_int
from oberon.assembler import cmps, opof, ops_rev


def dis(n):
    '''
    Take an integer and return a human-readable string description of the
    assembly instruction.
    '''
    IR = bint(n)
    k = IR[32:30]
    if   k == 0: value = dis_F0(IR)
    elif k == 1: value = dis_F1(IR)
    elif k == 2: value = dis_F2(IR)
    else:        value = dis_F3(IR)
    return value


def dis_F0(IR):
    u, a, b, op, c = IR[29], IR[28:24], IR[24:20], IR[20:16], IR[4:0]
    
    if ops_rev[op] == 'Mov':
        value = dis_Mov0(u, IR[28], a, c)

    elif ops_rev[op] == 'Mul':
        if u:
            value = 'mul (unsigned) R[%i] <- R[%i] R[%i]' % (a, b, c)
        else:
            value = 'mul R[%i] <- R[%i] R[%i]' % (a, b, c)

    elif ops_rev[op] in {'Add', 'Sub'}:
        if u:
            value = '%s (with Carry) R[%i] <- R[%i] R[%i]' % (opof(op).lower(), a, b, c)
        else:
            value = '%s R[%i] <- R[%i] R[%i]' % (opof(op).lower(), a, b, c)

    else:
        value = '%s R[%i] <- R[%i] R[%i]' % (opof(op).lower(), a, b, c)

    return value


def dis_Mov0(u, v, a, c):
    if u:
        if v:
            value = 'mov R[%i] <- (N,Z,C,OV, 0..01010000)' % (a,)
        else:
            value = 'mov R[%i] <- H' % (a,)
    else:
        value = 'mov R[%i] <- R[%i]' % (a, c)
    return value


def dis_F1(IR):
    u, v, a, b, op, imm = IR[29], IR[28], IR[28:24], IR[24:20], IR[20:16], IR[16:0]
    # Immediate values are extended to 32 bits with 16 v-bits to the left.
    if v:
        imm |= 0xffff0000

    if ops_rev[op] == 'Mov':
        if u: imm <<= 16
        value = 'mov R[%i] <- 0x%x' % (a, imm)

    elif ops_rev[op] == 'Mul':
        if u:
            value = 'mul (unsigned) R[%i] <- R[%i] 0x%x immediate' % (a, b, imm)
        else:
            value = 'mul R[%i] <- R[%i] 0x%x immediate' % (a, b, imm)

    elif ops_rev[op] in {'Add', 'Sub'}:
        if u:
            value = '%s (with Carry) R[%i] <- R[%i] 0x%x immediate' % (opof(op).lower(), a, b, imm)
        else:
            value = '%s R[%i] <- R[%i] 0x%x immediate' % (opof(op).lower(), a, b, imm)

    else:
        value = '%s R[%i] <- R[%i] 0x%x immediate' % (opof(op).lower(), a, b, imm)

    return value


def dis_F2(IR):
    a, b, off = IR[28:24], IR[24:20], IR[20:0]
    op, arrow = ('store', '->') if IR[29] else ('load', '<-')
    width = ' byte' if IR[28] else ''
    return '%s R[%i] %s [R[%i] + 0x%x]%s' % (op, a, arrow, b, off, width)


def dis_F3(IR):
    link = ' and R[15] <- PC + 1' if IR[28] else ''
    op = cmps[int(IR[27:24]), int(IR[27])]
    # I forget why int(...).
    if not IR[29]:
        value = 'BR %s R[%i]%s' % (op, IR[4:0], link)
    else:
        off = hex(signed_int_to_python_int(IR[24:0], width=24)).rstrip('L')
        value = 'BR %s %s immediate %s' % (op, off, link)
    return value
