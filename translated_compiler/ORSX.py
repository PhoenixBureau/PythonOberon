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
import sys

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

XWK = KWX.copy()
XWK[31] = 'ident'
XWK[52] = 'semicolon'
XWK[40] = 'comma'
XWK[1] = 'times'
XWK[9] = 'eql'
XWK[27] = 'not_'
XWK[18] = 'period'
XWK[5] = 'and_'
XWK[28] = 'lparen'
XWK[10] = 'neq'
XWK[21] = 'int_'
#XWK[] = ''
#XWK[] = ''
#XWK[] = ''

KWX = dict((v, k) for k, v in KWX.iteritems())

ival = 0
rval = 0.0
slen = 0

id_ = []

errpos = 0
errcnt = 0

ch = ''

str_  = [None] * stringBufSize

sym = null


R_eot = False
R = ''
_pos = 0


def TextsRead(r):
  global _pos
  try:
    _pos += 1
    c = r[_pos]
##    print >> sys.stderr, c,
    return c
  except IndexError:
    global R_eot
    R_eot = True
    return ''


def Init(text, pos=0):
  global errpos, errcnt, R_eot, R, _pos, ch
  errpos = pos
  _pos = pos-1
  errcnt = 0
  R_eot = False
  R = text
  ch = TextsRead(R)


def CopyId():
  global id_
  return ''.join(
    char
    for char in id_
    if char and isinstance(char, basestring)
    )


def Pos():
  return _pos - 1


def Mark(msg):
  global errpos, errcnt
  p = Pos()
  if p > errpos and errcnt < 25:
    print >> sys.stderr, "\npos %i %s" % (p, msg)
    raise ValueError
  errcnt += 1
  errpos = p + 4


def Identifier():
  global ch, sym
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


def String():
  global slen, ch
  i = 0
  ch = TextsRead(R)
  while not R_eot and (ch != '"'):
    if ch >= " ":
      if i < stringBufSize-1:
        str_[i] = ch
        i += 1
      else:
        Mark("string too long")
    ch = TextsRead(R)
  str_[i] = 0x0; i+=1; ch = TextsRead(R); slen = i


def HexString():
  global ch, slen
  i = 0; ch = TextsRead(R)
  while not R_eot and (ch != "$"):
    while (ch == " ") or (ch == 0x9) or (ch == 0x0D):
      ch = TextsRead(R)

    if ("0" <= ch) and (ch <= "9"):
      m = ord(ch) - 0x30
    elif ("A" <= ch) and (ch <= "F"):
      m = ord(ch) - 0x37
    else:
      m = 0
      Mark("hexdig expected")

    ch = TextsRead(R)

    if ("0" <= ch) and (ch <= "9"):
      n = ord(ch) - 0x30
    elif ("A" <= ch) and (ch <= "F"):
      n = ord(ch) - 0x37
    else:
      n = 0
      Mark("hexdig expected")

    if i < stringBufSize:
      str_[i] = chr(m * 0x10 + n)
      i += 1
    else:
      Mark("string too long")

    ch = TextsRead(R)

  ch = TextsRead(R)
  slen = i # (*no 0X appended!*)


def ODD(n):
  return int(n) == n and n % 2


def Ten(e):
  x = 1.0; t = 10.0;
  while e > 0:
    if ODD(e):
      x = t * x
    t = t * t; e = e / 2
  return x


def Number():
  global ival, rval, ch, k, sym
  max = 2147483647 # (*2^31*);
  maxM = 16777216; # (*2^24*)
  d = [None] * 16

  ival = 0; i = 0; n = 0; k = 0;

  while True:
    if n < 16:
      d[n] = ord(ch)-0x30
      n += 1
    else:
      Mark("too many digits")
      n = 0
    ch = TextsRead(R)
    if (ch < "0") or (ch > "9") and (ch < "A") or (ch > "F"):
      break

  if (ch == "H") or (ch == "R") or (ch == "X"): #  (*hex*)
    while True:
      h = d[i]
      if h >= 10:
        h = h-7
      k = k * 0x10 + h
      i += 1 # (*no overflow check*)
      if i == n:
        break
    if ch == "X":
      sym = char;
      if k < 0x100:
        ival = k
      else:
        Mark("illegal value")
        ival = 0
    elif ch == "R":
      sym = real
      rval = float(k)
    else:
      sym = int_
      ival = k

    ch = TextsRead(R)

  elif ch == ".":
    ch = TextsRead(R)
    if ch == ".": # (*double dot*)
      ch = 0x7F # (*decimal integer*)
      while True:
        if d[i] < 10:
          h = k*10 + d[i]
          if h < max:
            k = h
          else:
            Mark("too large")
        else:
          Mark("bad integer")
        i += 1
        if i == n:
          break
      sym = int_
      ival = k

    else: # (*real number*)
      x = 0.0; e = 0;
      while True: # (*integer part*)
        h = k*10 + d[i]
        if h < maxM:
          k = h
        else:
          Mark("too many digits")
        i += 1
        if i == n:
          break
      while (ch >= "0") and (ch <= "9"): # (*fraction*)
        h = k*10 + ord(ch) - 0x30
        if h < maxM:
          k = h
        else:
          Mark("too many digits*")
        e -= 1
        ch = TextsRead(R)

      x = float(k)
      if (ch == "E") or (ch == "D"): # (*scale factor*)
        ch = TextsRead(R)
        s = 0 
        if ch == "-":
          negE = True
          ch = TextsRead(R)
        else:
          negE = False
          if ch == "+":
            ch = TextsRead(R)

        if (ch >= "0") & (ch <= "9"):
          while True:
            s = s*10 + ord(ch)-0x30
            ch = TextsRead(R)
            if (ch < "0") or (ch >"9"):
              break
          if negE:
            e = e-s
          else:
            e = e+s
        else:
          Mark("digit?")

      if e < 0:
        if e >= -maxExp:
          x = x / Ten(-e)
        else:
          x = 0.0
      elif e > 0:
        if e <= maxExp:
          x = Ten(e) * x
        else:
          x = 0.0
          Mark("too large")

      sym = real
      rval = x

  else: #  (*decimal integer*)
    while True:
      if d[i] < 10:
        if k <= (max-d[i]) / 10:
          k = k*10 + d[i]
        else:
          Mark("too large")
          k = 0
      else:
        Mark("bad integer")

      i += 1
      if i == n:
        break
    sym = int_
    ival = k


def comment():
  global ch
  ch = TextsRead(R)
  while True:
    while not R_eot and (ch != "*"):
      if ch == "(":
        ch = TextsRead(R)
        if ch == "*":
          comment()
      else:
        ch = TextsRead(R)

    while ch == "*":
      ch = TextsRead(R)
    if (ch == ")") or R_eot:
      break
  if not R_eot:
    ch = TextsRead(R)
  else:
    Mark("unterminated comment")


def Get():
  global sym, ch
  while True:
    while not R_eot and (ch <= " "):
      ch = TextsRead(R)
    if ch < "A":
      if ch < "0":
        if ch == '"':
          String()
          sym = string
        elif ch == "#":
          ch = TextsRead(R)
          sym = neq
        elif ch == "$":
          HexString()
          sym = string
        elif ch == "&":
          ch = TextsRead(R)
          sym = and_
        elif ch == "(":
          ch = TextsRead(R); 
          if ch == "*":
            sym = null
            comment()
          else:
            sym = lparen
        elif ch == ")":
          ch = TextsRead(R)
          sym = rparen
        elif ch == "*":
          ch = TextsRead(R)
          sym = times
        elif ch == "+":
          ch = TextsRead(R)
          sym = plus
        elif ch == ",":
          ch = TextsRead(R)
          sym = comma
        elif ch == "-":
          ch = TextsRead(R)
          sym = minus
        elif ch == ".":
          ch = TextsRead(R);
          if ch == ".":
            ch = TextsRead(R)
            sym = upto
          else:
            sym = period
        elif ch == "/":
          ch = TextsRead(R)
          sym = rdiv
        else:
          ch = TextsRead(R) # (* ! % ' *)
          sym = null

      elif ch < ":":
        Number()
      elif ch == ":" :
        ch = TextsRead(R);
        if ch == "=" :
          ch = TextsRead(R)
          sym = becomes
        else:
          sym = colon

      elif ch == ";" :
        ch = TextsRead(R)
        sym = semicolon
      elif ch == "<" :
        ch = TextsRead(R)
        if ch == "=" :
          ch = TextsRead(R)
          sym = leq
        else:
          sym = lss

      elif ch == "=" :
        ch = TextsRead(R)
        sym = eql
      elif ch == ">" :
        ch = TextsRead(R)
        if ch == "=" :
          ch = TextsRead(R)
          sym = geq
        else:
          sym = gtr
      else: # (* ? @ *)
        ch = TextsRead(R)
        sym = null

    elif ch < "[":
      Identifier()

    elif ch < "a":
      if ch == "[":
        sym = lbrak
      elif ch == "]":
        sym = rbrak
      elif ch == "^":
        sym = arrow
      else: # (* _ ` *)
        sym = null
      ch = TextsRead(R)

    elif ch < "{":
      Identifier()
    else:
      if ch == "{":
        sym = lbrace
      elif ch == "}":
        sym = rbrace
      elif ch == "|":
        sym = bar
      elif ch == "~":
        sym = not_
      elif ch == 0x7F:
        sym = upto
      else:
        sym = null

      ch = TextsRead(R)

    if sym != null or R_eot:
      break
  return sym
