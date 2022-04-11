from oberon.util import bint, signed_int_to_python_int
from oberon.assembler import cmps, opof, ops_rev


def dis(n):
    '''
    Take an integer and return the assembly instruction.
    '''
    IR = bint(n)
    return INSTRUCTION_FORMATS[IR[32:30]](IR)


def dis_F0(IR):
    u, a, b, op, c = IR[29], IR[28:24], IR[24:20], IR[20:16], IR[4:0]
    if ops_rev[op] == 'Mov':
        value = dis_Mov0(u, IR[28], a, c)
    else:
        value = f'{opof(op)({a}, {b}, {c}, u={u})}'
    return value


def dis_Mov0(u, v, a, c):
    if u:
        if v:
            value = 'mov R[%i] <- (N,Z,C,OV, 0..01010000)' % (a,)
        else:
            value = 'mov R[%i] <- H' % (a,)
    else:
        value = f'Mov({a}, {c}, u={u})'
    return value


def dis_F1(IR):
    u, v, a, b, op, imm = IR[29], IR[28], IR[28:24], IR[24:20], IR[20:16], IR[16:0]
    if ops_rev[op] == 'Mov':
        value = f'Mov_imm({a}, 0x{imm:x}, v={v}, u={u})'
    else:
        value = f'{opof(op)}_imm({a}, {b}, 0x{imm:x}, v={v}, u={u})'
    return value

_ram_instrs = {
    # IR[29], IR[28]
    (True,   True): 'Store_byte',
    (True,  False): 'Store_word',
    (False,  True): 'Load_byte',
    (False, False): 'Load_word',
    }

def dis_F2(IR):
    a, b, off = IR[28:24], IR[24:20], IR[20:0]
    fn = _ram_instrs[IR[29], IR[28]]
    if off:
        value = f'{fn}({a}, {b}, offset={hex(off)})'
    else:
        value = f'{fn}({a}, {b})'
    return value


def dis_F3(IR):
    op = cmps[int(IR[27:24]), int(IR[27])]  # I forget why int(...).
    if not IR[29]:
        if IR[28]:
            value = f'{op}_link({IR[4:0]})'
        else:
            value = f'{op}({IR[4:0]})'
    else:
        off = signed_int_to_python_int(IR[24:0], width=24)
        value = f'{op}_imm({hex(off)})'
    return value


INSTRUCTION_FORMATS = dis_F0, dis_F1, dis_F2, dis_F3
