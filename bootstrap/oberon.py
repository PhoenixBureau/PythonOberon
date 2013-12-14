#!/usr/bin/env python
'''
'''
from omega import BaseParser


def realize(s, e, sc):
  f = float("".join(s)+'.'+"".join(e))
  if sc is not None:
    f *= 10**sc
  return f


class OberonParser(BaseParser):
  __grammar = '''

    uppercase = 'A' | 'B' | 'C' | 'D' | 'E' | 'F' | 'G' | 'H' | 'I'
                    | 'J' | 'K' | 'L' | 'M' | 'N' | 'O' | 'P' | 'Q' | 'R' | 'S'
                    | 'T' | 'U' | 'V' | 'W' | 'X' | 'Y' | 'Z' ;
    lowercase = 'a' | 'b' | 'c' | 'd' | 'e' | 'f' | 'g' | 'h' | 'i'
                    | 'j' | 'k' | 'l' | 'm' | 'n' | 'o' | 'p' | 'q' | 'r' | 's'
                    | 't' | 'u' | 'v' | 'w' | 'x' | 'y' | 'z' ;
    digit = '0' | '1' | '2' | '3' | '4' | '5' | '6' | '7' | '8' | '9' ;
    hexdigit = digit | 'A' | 'B' | 'C' | 'D' | 'E' | 'F' ;

    letter = uppercase | lowercase ;

    identChar = letter | digit ;

    ident = letter:start identChar*:rest -> (start + "".join(rest));

    number = real | integer ;
    integer = digit+:i -> (int("".join(i))) |
              hexdigit+:i 'H' -> (int("".join(i), 16)) ;

    scalefactor = ( 'E'| 'D' ) ( '+' | '-' )?:scsign digit+:sc -> (int((scsign or "") + "".join(sc))) ;

    real = digit+:s '.' digit*:e scalefactor?:sc -> (realize(s, e, sc)) ;

    charconstant = '"' anything:ch '"' -> (ch) | hexdigit+:hch 'X' -> (chr(int("".join(hch), 16))) ;

    string = '"' (~exactly('"') anything)*:st '"' -> ("".join(st)) ;

    oberon = charconstant | string | number | ident ;
    '''

if __name__ == '__main__':
  for inp in '''

    hi
    23
    FFH
    2.3
    6.

    2.7E3
    2.7E-3

    "h" 40X

    "23" ""

  '''.split():
    print repr(OberonParser.match(inp))
