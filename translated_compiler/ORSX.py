'''
MODULE ORS; (* NW 19.9.93 / 10.10.2013  Scanner in Oberon-07*)
  IMPORT SYSTEM, Texts, Oberon;

(* Oberon Scanner does lexical analysis. Input is Oberon-Text, output is
  sequence of symbols, i.e identifiers, numbers, strings, and special symbols.
  Recognises all Oberon keywords and skips comments. The keywords are
  recorded in a table.
  Get(sym) delivers next symbol from input text with Reader R.
  Mark(msg) records error and delivers error message with Writer W.
  If Get delivers ident, then the identifier (a string) is in variable id, if int or char
  in ival, if real in rval, and if string in str (and slen) *)
'''
#  CONST
IdLen = 32; WS = 4; # (*Word size*)
NKW = 34; # (*nof keywords*)
maxExp = 38; stringBufSize = 256;
  
#    (*lexical symbols*)
null = 0; times = 1; rdiv = 2; div = 3; mod = 4;
and_ = 5; plus = 6; minus = 7; or_ = 8; eql = 9;
neq = 10; lss = 11; leq = 12; gtr = 13; geq = 14;
in_ = 15; is_ = 16; arrow = 17; period = 18;
char = 20; int_ = 21; real = 22; false = 23; true = 24;
nil = 25; string = 26; not_ = 27; lparen = 28; lbrak = 29;
lbrace = 30; ident = 31;
if_ = 32; while_ = 34; repeat = 35; case = 36; for_ = 37;
comma = 40; colon = 41; becomes = 42; upto = 43; rparen = 44;
rbrak = 45; rbrace = 46; then = 47; of = 48; do = 49;
to = 50; by = 51; semicolon = 52; end = 53; bar = 54;
else_ = 55; elsif = 56; until = 57; return_ = 58;
array = 60; record = 61; pointer = 62; const = 63; type_ = 64;
var = 65; procedure = 66; begin = 67; import_ = 68; module = 69;
eof = 70;

KWX = {}
KWX[if_] = "IF"
KWX[do] = "DO"
KWX[of] = "OF"
KWX[or_] = "OR"
KWX[to] = "TO"
KWX[in_] = "IN"
KWX[is_] = "IS"
KWX[by] = "BY"
KWX[end] = "END"
KWX[nil] = "NIL"
KWX[var] = "VAR"
KWX[div] = "DIV"
KWX[mod] = "MOD"
KWX[for_] = "FOR"
KWX[else_] = "ELSE"
KWX[then] = "THEN"
KWX[true] = "TRUE"
KWX[type_] = "TYPE"
KWX[case] = "CASE"
KWX[elsif] = "ELSIF"
KWX[false] = "FALSE"
KWX[array] = "ARRAY"
KWX[begin] = "BEGIN"
KWX[const] = "CONST"
KWX[until] = "UNTIL"
KWX[while_] = "WHILE"
KWX[record] = "RECORD"
KWX[repeat] = "REPEAT"
KWX[return_] = "RETURN"
KWX[import_] = "IMPORT"
KWX[module] = "MODULE"
KWX[pointer] = "POINTER"
KWX[procedure] = "PROCEDURE"
KWX = dict((v, k) for k, v in KWX.iteritems())

'''
  TYPE Ident* = ARRAY IdLen OF CHAR;

  VAR ival*, slen*: LONGINT;  (*results of Get*)
    rval*: REAL;
'''

slen = 0

id_ = []

R_eot = False
R = open('ORSX.Mod.txt').read()
_R = iter(R)
_pos = 0
def TextsRead(r):
  global _pos
  try:
    _pos += 1
    return next(_R)
  except StopIteration:
    global R_eot
    R_eot = True
    return ''

errpos = 0
errcnt = 0

ch = ''

str_  = [None] * stringBufSize


'''
    ch: CHAR;  (*last character read*)
    R: Texts.Reader;
    W: Texts.Writer;
    k: INTEGER;
    KWX: ARRAY 10 OF INTEGER;
    keyTab: ARRAY NKW OF
        RECORD sym: INTEGER; id: ARRAY 12 OF CHAR END;
'''

##  PROCEDURE CopyId*(VAR ident: Ident);
##  BEGIN ident := id
##  END CopyId;

def CopyId(ident):
  global id_
  ident[:] = id_[:]

##  PROCEDURE Pos*(): LONGINT;
##  BEGIN RETURN Texts.Pos(R) - 1
##  END Pos;

def Pos():
  return _pos - 1

##  PROCEDURE Mark*(msg: ARRAY OF CHAR);
##    VAR p: LONGINT;
##  BEGIN p := Pos();
##    IF (p > errpos) & (errcnt < 25) THEN
##      Texts.WriteLn(W); Texts.WriteString(W, "  pos "); Texts.WriteInt(W, p, 1); Texts.Write(W, " ");
##      Texts.WriteString(W, msg); Texts.Append(Oberon.Log, W.buf)
##    END ;
##    INC(errcnt); errpos := p + 4
##  END Mark;

def Mark(msg):
  global errpos, errcnt
  p = Pos()
  if p > errpos and errcnt < 25:
    print "pos", p, msg
  errcnt += 1
  errpos = p + 4

##  PROCEDURE Identifier(VAR sym: INTEGER);
##    VAR i, k: INTEGER;
##  BEGIN i := 0;
##    REPEAT
##      IF i < IdLen-1 THEN id[i] := ch; i += 1 END ;
##      ch = TextsRead(R)
##    UNTIL (ch < "0") OR (ch > "9") & (ch < "A") OR (ch > "Z") & (ch < "a") OR (ch > "z");
##    id[i] := 0X; 
##    IF i < 10 THEN k := KWX[i-1];  (*search for keyword*)
##      WHILE (id # keyTab[k].id) & (k < KWX[i]) DO INC(k) END ;
##      IF k < KWX[i] THEN sym := keyTab[k].sym ELSE sym := ident END
##    ELSE sym := ident
##    END
##  END Identifier;

def Identifier(sym=None):
  global ch
  del id_[:]
  i = 0
  while True:
    if i < IdLen - 1:
      id_.append(ch)
      i += 1
    ch = TextsRead(R)
    if not ch.isalnum():
      break
  if i < 10:
    try:
      sym = KWX[''.join(id_)]
    except KeyError:
      sym = ident
  else:
    sym = ident
  return sym


##  PROCEDURE String;
##    VAR i: INTEGER;
##  BEGIN i := 0; ch = TextsRead(R);
##    WHILE ~R.eot & (ch # 22X) DO
##      IF ch >= " " THEN
##        IF i < stringBufSize-1 THEN str[i] := ch; i += 1 ELSE Mark("string too long") END ;
##      END ;
##      ch = TextsRead(R)
##    END ;
##    str[i] := 0X; i += 1; ch = TextsRead(R); slen := i
##  END String;


def String():
  global slen, ch
  i = 0
  ch = TextsRead(R)
  while not R_eot and (ch != 0x22):
    if ch >= " ":
      if i < stringBufSize-1:
        str_[i] = ch
        i += 1
      else:
        Mark("string too long")
    ch = TextsRead(R)
  str_[i] = 0x0; i+=1; ch = TextsRead(R); slen = i

##  PROCEDURE HexString;
##    VAR i, m, n: INTEGER;
##  BEGIN i := 0; ch = TextsRead(R);
##    WHILE ~R.eot & (ch # "$") DO
##      WHILE (ch = " ") OR (ch = 9X) OR (ch = 0DX) DO ch = TextsRead(R) END ;  (*skip*)
##      IF ("0" <= ch) & (ch <= "9") THEN m := ORD(ch) - 30H
##      ELSIF ("A" <= ch) & (ch <= "F") THEN m := ORD(ch) - 37H
##      ELSE m := 0; Mark("hexdig expected")
##      END ;
##      ch = TextsRead(R);
##      IF ("0" <= ch) & (ch <= "9") THEN n := ORD(ch) - 30H
##      ELSIF ("A" <= ch) & (ch <= "F") THEN n := ORD(ch) - 37H
##      ELSE n := 0; Mark("hexdig expected")
##      END ;
##      IF i < stringBufSize THEN str[i] := CHR(m*10H + n); i += 1 ELSE Mark("string too long") END ;
##      ch = TextsRead(R)
##    END ;
##    ch = TextsRead(R); slen := i  (*no 0X appended!*)
##  END HexString;

def HexString():
  i = 0; ch = TextsRead(R);
  while not R_eot and (ch != "$"):
    while (ch == " ") or (ch == 0x9) or (ch == 0x0D):
      ch = TextsRead(R)

    if ("0" <= ch) and (ch <= "9"):
      m = ord(ch) - 0x30
    elif ("A" <= ch) and (ch <= "F"):
      m = ord(ch) - 0x37
    else:
      m = 0; Mark("hexdig expected")

    ch = TextsRead(R);

    if ("0" <= ch) and (ch <= "9"):
      n = ord(ch) - 0x30
    elif ("A" <= ch) and (ch <= "F"):
      n = ord(ch) - 0x37
    else:
      n = 0; Mark("hexdig expected")

    if i < stringBufSize:
      str_[i] = chr(m * 0x10 + n); i += 1
    else:
      Mark("string too long")

    ch = TextsRead(R)

  ch = TextsRead(R); slen = i # (*no 0X appended!*)


'''
  PROCEDURE Ten(e: LONGINT): REAL;
    VAR x, t: REAL;
  BEGIN x := 1.0; t := 10.0;
    WHILE e > 0 DO
      IF ODD(e) THEN x := t * x END ;
      t := t * t; e := e DIV 2
    END ;
    RETURN x
  END Ten;

  PROCEDURE Number(VAR sym: INTEGER);
    CONST max = 2147483647 (*2^31*); maxM = 16777216; (*2^24*)
    VAR i, k, e, n, s, h: LONGINT; x: REAL;
      d: ARRAY 16 OF INTEGER;
      negE: BOOLEAN;
  BEGIN ival := 0; i := 0; n := 0; k := 0;
    REPEAT
      IF n < 16 THEN d[n] := ORD(ch)-30H; INC(n) ELSE Mark("too many digits"); n := 0 END ;
      ch = TextsRead(R)
    UNTIL (ch < "0") OR (ch > "9") & (ch < "A") OR (ch > "F");
    IF (ch = "H") OR (ch = "R") OR (ch = "X") THEN  (*hex*)
      REPEAT h := d[i];
        IF h >= 10 THEN h := h-7 END ;
        k := k*10H + h; i += 1 (*no overflow check*)
      UNTIL i = n;
      IF ch = "X" THEN sym := char;
        IF k < 100H THEN ival := k ELSE Mark("illegal value"); ival := 0 END
      ELSIF ch = "R" THEN sym := real; rval := SYSTEM.VAL(REAL, k)
      ELSE sym := int; ival := k
      END ;
      ch = TextsRead(R)
    ELSIF ch = "." THEN
      ch = TextsRead(R);
      IF ch = "." THEN (*double dot*) ch := 7FX;  (*decimal integer*)
        REPEAT
          IF d[i] < 10 THEN
            h := k*10 + d[i];
            IF h < max THEN k := h ELSE Mark("too large") END
          ELSE Mark("bad integer")
          END ;
          i += 1
        UNTIL i = n;
        sym := int; ival := k
      ELSE (*real number*) x := 0.0; e := 0;
        REPEAT (*integer part*) h := k*10 + d[i];
          IF h < maxM THEN k := h ELSE Mark("too many digits") END ;
          i += 1
        UNTIL i = n;
        WHILE (ch >= "0") & (ch <= "9") DO (*fraction*)
          h := k*10 + ORD(ch) - 30H;
          IF h < maxM THEN k := h ELSE Mark("too many digits*") END ;
          DEC(e); ch = TextsRead(R)
        END ;
        x := FLT(k);
        IF (ch = "E") OR (ch = "D") THEN  (*scale factor*)
          ch = TextsRead(R); s := 0; 
          IF ch = "-" THEN negE := TRUE; ch = TextsRead(R)
          ELSE negE := FALSE;
            IF ch = "+" THEN ch = TextsRead(R) END
          END ;
          IF (ch >= "0") & (ch <= "9") THEN
            REPEAT s := s*10 + ORD(ch)-30H; ch = TextsRead(R)
            UNTIL (ch < "0") OR (ch >"9");
            IF negE THEN e := e-s ELSE e := e+s END
          ELSE Mark("digit?")
          END
        END ;
        IF e < 0 THEN
          IF e >= -maxExp THEN x := x / Ten(-e) ELSE x := 0.0 END
        ELSIF e > 0 THEN
          IF e <= maxExp THEN x := Ten(e) * x ELSE x := 0.0; Mark("too large") END
        END ;
        sym := real; rval := x
      END
    ELSE  (*decimal integer*)
      REPEAT
        IF d[i] < 10 THEN
          IF k <= (max-d[i]) DIV 10 THEN k := k*10 + d[i] ELSE Mark("too large"); k := 0 END
        ELSE Mark("bad integer")
        END ;
        i += 1
      UNTIL i = n;
      sym := int; ival := k
    END
  END Number;

  PROCEDURE comment;
  BEGIN ch = TextsRead(R);
    REPEAT
      WHILE ~R.eot & (ch # "*") DO
        IF ch = "(" THEN ch = TextsRead(R);
          IF ch = "*" THEN comment END
        ELSE ch = TextsRead(R)
        END
      END ;
      WHILE ch = "*" DO ch = TextsRead(R) END
    UNTIL (ch = ")") OR R.eot;
    IF ~R.eot THEN ch = TextsRead(R) ELSE Mark("unterminated comment") END
  END comment;

  PROCEDURE Get*(VAR sym: INTEGER);
  BEGIN
    REPEAT
      WHILE ~R.eot & (ch <= " ") DO ch = TextsRead(R) END;
      IF ch < "A" THEN
        IF ch < "0" THEN
          IF ch = 22X THEN String; sym := string
          ELSIF ch = "#" THEN ch = TextsRead(R); sym := neq
          ELSIF ch = "$" THEN HexString; sym := string
          ELSIF ch = "&" THEN ch = TextsRead(R); sym := and
          ELSIF ch = "(" THEN ch = TextsRead(R); 
            IF ch = "*" THEN sym := null; comment ELSE sym := lparen END
          ELSIF ch = ")" THEN ch = TextsRead(R); sym := rparen
          ELSIF ch = "*" THEN ch = TextsRead(R); sym := times
          ELSIF ch = "+" THEN ch = TextsRead(R); sym := plus
          ELSIF ch = "," THEN ch = TextsRead(R); sym := comma
          ELSIF ch = "-" THEN ch = TextsRead(R); sym := minus
          ELSIF ch = "." THEN ch = TextsRead(R);
            IF ch = "." THEN ch = TextsRead(R); sym := upto ELSE sym := period END
          ELSIF ch = "/" THEN ch = TextsRead(R); sym := rdiv
          ELSE ch = TextsRead(R); (* ! % ' *) sym := null
          END
        ELSIF ch < ":" THEN Number(sym)
        ELSIF ch = ":" THEN ch = TextsRead(R);
          IF ch = "=" THEN ch = TextsRead(R); sym := becomes ELSE sym := colon END 
        ELSIF ch = ";" THEN ch = TextsRead(R); sym := semicolon
        ELSIF ch = "<" THEN  ch = TextsRead(R);
          IF ch = "=" THEN ch = TextsRead(R); sym := leq ELSE sym := lss END
        ELSIF ch = "=" THEN ch = TextsRead(R); sym := eql
        ELSIF ch = ">" THEN ch = TextsRead(R);
          IF ch = "=" THEN ch = TextsRead(R); sym := geq ELSE sym := gtr END
        ELSE (* ? @ *) ch = TextsRead(R); sym := null
        END
      ELSIF ch < "[" THEN Identifier(sym)
      ELSIF ch < "a" THEN
        IF ch = "[" THEN sym := lbrak
        ELSIF ch = "]" THEN  sym := rbrak
        ELSIF ch = "^" THEN sym := arrow
        ELSE (* _ ` *) sym := null
        END ;
        ch = TextsRead(R)
      ELSIF ch < "{" THEN Identifier(sym) ELSE
        IF ch = "{" THEN sym := lbrace
        ELSIF ch = "}" THEN sym := rbrace
        ELSIF ch = "|" THEN sym := bar
        ELSIF ch = "~" THEN  sym := not
        ELSIF ch = 7FX THEN  sym := upto
        ELSE sym := null
        END ;
        ch = TextsRead(R)
      END
    UNTIL sym # null
  END Get;

  PROCEDURE Init*(T: Texts.Text; pos: LONGINT);
  BEGIN errpos := pos; errcnt := 0; Texts.OpenReader(R, T, pos); ch = TextsRead(R)
  END Init;

  PROCEDURE EnterKW(sym: INTEGER; name: ARRAY OF CHAR);
  BEGIN keyTab[k].id := name; keyTab[k].sym := sym; INC(k)
  END EnterKW;

'''
