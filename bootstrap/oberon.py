#!/usr/bin/env python
'''
'''
import omega


test_strings = [line.strip() for line in '''

    a =23
    a=FFH
    bar=2.3
    ney*=6.

    a=2.7E3
    a=2.7E-3

    a = hi
    a = he.llo
    a = "h"
    a = 40X

    a = "23"
    a = ""

    g = ARRAY 3 OF INTEGER
    g = ARRAY 3 OF ARRAY 3, 8 OF INTEGER

  '''.splitlines() if line and not line.isspace()]


RESERVED_WORDS = set('''\
  ARRAY
  '''.split())


BASE_TYPES = set('''\
  INTEGER
  '''.split())


def realize(s, e, sc):
  f = float("".join(s)+'.'+"".join(e))
  if sc is not None:
    f *= 10**sc
  return f


class Qualident:
  def __init__(self, a, b):
    self.a, self.b = a, b
    self.value = b if a is None else (a + '.' + b)
  def __repr__(self):
    return 'Qualident(' + self.value + ')'


class IdentDef:
  def __init__(self, i, public):
    self.i, self.public = i, public
    self.value = i if public is None else (i + '*')
  def __repr__(self):
    return 'IdentDef(' + self.value + ')'


class Const:
  def __init__(self, i, e):
    self.i, self.e = i, e
    self.value = [i, e]
  def __repr__(self):
    return 'Const(%s)' % (self.value,)


class Typ:
  def __init__(self, i, e):
    self.i, self.e = i, e
    self.value = [i, e]
  def __repr__(self):
    return 'Typ(%s)' % (self.value,)


class Array:
  def __init__(self, i, e):
    self.i, self.e = i, e
    self.value = [i, e]
  def __repr__(self):
    return 'Array(%s)' % (self.value,)


class OberonParser(omega.BaseParser):
  __grammar = '''

    space = ' ' | '\r' | '\n' | '\t' ;
    spaces = space*;

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

    uident = letter:start identChar*:rest -> (start + "".join(rest)) ;
    ident = uident:w ?(w not in RESERVED_WORDS) -> (w);

    qualident = (ident:a '.' -> (a))?:c ident:b -> (Qualident(c, b)) ;
    identdef = ident:i '*'?:public -> (IdentDef(i, public)) ;

    number = real | integer ;
    integer = digit+:i -> (int("".join(i))) |
              hexdigit+:i 'H' -> (int("".join(i), 16)) ;

    scalefactor = ( 'E'| 'D' ) ( '+' | '-' )?:scsign digit+:sc -> (int((scsign or "") + "".join(sc))) ;

    real = digit+:s '.' digit*:e scalefactor?:sc -> (realize(s, e, sc)) ;

    charconstant = '"' anything:ch '"' -> (ch) | hexdigit+:hch 'X' -> (chr(int("".join(hch), 16))) ;

    string = '"' (~exactly('"') anything)*:st '"' -> ("".join(st)) ;

    expression = charconstant | string | number | qualident ;

    ConstExpression = expression ;
    ConstantDeclaration = identdef:i spaces '=' spaces ConstExpression:e -> (Const(i, e)) ;

    typ = qualident | ArrayType ;
    TypeDeclaration = identdef:i spaces '=' spaces typ:e -> (Typ(i, e)) ;

    length = ConstExpression ;
    indicies = length:head (spaces ',' spaces length)*:tail -> ([head] + tail) ;
    ArrayType = "ARRAY" spaces indicies:ind spaces "OF" spaces typ:t -> (Array(ind, t)) ;

    oberon = ConstantDeclaration | TypeDeclaration ;
    '''

if __name__ == '__main__':
  for inp in test_strings:
    print repr(inp), '->', repr(OberonParser.match(inp))
