PYOBERON=python -m oberon
OFRTH=oberonforth
EPILOG=' ; Hi $$2 $$5 $$48 paint_char $$2 $$6 $$69 paint_char ; Hi '
ADD=../fonts/8x13.bintoo

.PHONY: clean

all: $(OFRTH).bin

clean:
	$(RM) $(OFRTH).bin $(OFRTH).symbols

$(OFRTH).bin: $(OFRTH).py
	$(PYOBERON) assemble $(OFRTH).py $(OFRTH).bin -s $(OFRTH).symbols -e $(EPILOG) -a $(ADD) -p > assembler.output.txt
