from myhdl import always


_i = lambda ibvsig: int(ibvsig.val)


def sparseMemory(memory, dout, din, addr, we, en, clk):

    """ Sparse memory model based on a dictionary.

    Ports:
    dout -- data out
    din -- data in
    addr -- address bus
    we -- write enable: write if 1, read otherwise
    en -- interface enable: enabled if 0
    clk -- clock input

    """
    @always(clk.posedge)
    def access():
        if not en:
            if we:
                memory[_i(addr)] = _i(din)
            else:
                dout.next = memory[_i(addr)]

    return access
