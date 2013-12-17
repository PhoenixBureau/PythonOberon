#!/usr/bin/env python
'''
'''
import omega
from ObAST import (
  RESERVED_WORDS,
  realize,
  Qualident,
  IdentDef,
  Const,
  Typ,
  Array,
  )


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
    g = ARRAY 3 OF POINTER TO INTEGER

    r = RECORD barry:INTEGER END
    r = RECORD(h.i) barry:INTEGER END
    r = RECORD barry, larry, gary:INTEGER END
    r = RECORD barry:INTEGER ; gary:INTEGER END
    r = RECORD barry: ARRAY 3 OF INTEGER END

    i,j, k: INTEGER

  '''.splitlines() if line and not line.isspace()]


class OberonParser(omega.BaseParser):
  __grammar = '''

    space = ' ' | '\r' | '\n' | '\t' ;
    spaces = space*;
    token :t = spaces seq(t);

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

    typ = qualident | ArrayType | RecordType | PointerType ;
    TypeDeclaration = identdef:i spaces '=' spaces typ:e -> (Typ(i, e)) ;

    length = ConstExpression ;
    indicies = length:head (spaces ',' spaces length)*:tail -> ([head] + tail) ;
    ArrayType = "ARRAY" spaces indicies:ind spaces "OF" spaces typ:t -> (Array(ind, t)) ;

    BaseType = qualident ;
    FieldListSequence = spaces FieldList:head spaces ( ';' spaces FieldList )*:tail -> ([head] + tail) ;
    FieldList = IdentList:idl ':' typ:t -> ((idl, t)) ;
    IdentList = spaces identdef:head ( ',' spaces identdef )*:tail -> ([head] + tail) ;
    RecordType = "RECORD" spaces
                   ( '(' spaces BaseType:a spaces ')' -> (a) )?:basetype
                   FieldListSequence:fls
                 spaces "END"
                 ->
                 ((basetype, fls)) ;

    PointerType = "POINTER" spaces "TO" spaces typ:t -> (("POINTER", t)) ;

    VariableDeclaration = IdentList:i spaces ':' spaces typ:t -> (("var", i, t)) ;

    oberon = ConstantDeclaration | TypeDeclaration | VariableDeclaration ;
    '''

if __name__ == '__main__':
  for inp in test_strings:
    print repr(inp), '->', repr(OberonParser.match(inp))
