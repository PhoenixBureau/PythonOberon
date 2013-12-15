'''
  PROCEDURE Put3(op, cond, off: LONGINT);
  BEGIN (*emit branch instruction*)
    code[pc] := ((op+12) * 10H + cond) * 1000000H + (off MOD 1000000H); INC(pc)
  END Put3;

'''

def Put3(op, cond, off):
  return bin(
    ((op+12) * 0x10 + cond) * 0x1000000 + (off % 0x1000000)
    )[2:]

print Put3(2, 7, 3)
print Put3(3, 15, 15)
print Put3(-11, 1, 1)
print Put3(4, 16, 16)

11100111000000000000000000000011
11111111000000000000000000001111
00010001000000000000000000000001
100010000000000000000000000010000

##reg N, Z, C, OV; // condition flags
##wire S;
##assign S = N ^ OV;
##assign cond = IR[27] ^
##((cc == 0) & N |
##// MI, PL
##(cc == 1) & Z |
##// EQ, NE
##(cc == 2) & C |
##// CS, CC
##(cc == 3) & OV |
##// VS, VC
##(cc == 4) & (C|Z) |
##// LS, HI
##(cc == 5) & S |
##// LT, GE
##11
##(cc == 6) & (S|Z) |
##(cc == 7));
##// LE, GT
##// T, F
