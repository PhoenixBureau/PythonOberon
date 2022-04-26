PYOBERON=python -m oberon
OFRTH=oberonforth
EPILOG=' ; Hi $$2 $$5 $$48 paint_char $$2 $$6 $$69 paint_char ; Hi '
ADD=../fonts/8x13.bintoo

.PHONY: clean

all: $(OFRTH).bin

clean:
	$(RM) $(OFRTH).bin $(OFRTH).symbols

$(OFRTH).bin: $(OFRTH).py $(OFRTH).$(OFRTH)
	$(PYOBERON) assemble $(OFRTH).py $(OFRTH).0.bin -s $(OFRTH).symbols -a $(ADD) -p > assembler.output.txt
	cat $(OFRTH).0.bin $(OFRTH).$(OFRTH) > $(OFRTH).bin

#  -e $(EPILOG)