PYOBERON=python -m oberon
OFRTH=oberonforth
EPILOG=' $$48 EMIT $$69 EMIT $$48 EMIT '
ADD=../fonts/8x13.bintoo

.PHONY: clean

all: $(OFRTH).bin

clean:
	$(RM) $(OFRTH).bin $(OFRTH).symbols

$(OFRTH).bin: $(OFRTH).py
	$(PYOBERON) assemble $(OFRTH).py $(OFRTH).bin -s $(OFRTH).symbols -e $(EPILOG) -a $(ADD) -p > assembler.output.txt
