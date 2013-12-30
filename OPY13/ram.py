from myhdl import always


_i = lambda ibvsig: int(ibvsig.val)


def sparseMemory(memory, dout, din, addr, we, clk):

    """ Sparse memory model based on a dictionary.

    Ports:
    dout -- data out
    din -- data in
    addr -- address bus
    we -- write enable: write if 1, read otherwise
    clk -- clock input

    """
    @always(clk.posedge)
    def access():
        print 'addr, din, dout, we'
        print addr, din, dout, we
        print # 'AHA!', 1/0
        if we:
            memory[_i(addr)] = _i(din)
        else:
            dout.next = memory[_i(addr)]

    return access
