PYOBERON=python -m oberon
OFRTH=oberonforth
EPILOG=


.PHONY: clean

all: $(OFRTH).bin

clean:
	$(RM) $(OFRTH).bin $(OFRTH).symbols

$(OFRTH).bin: $(OFRTH).py
	$(PYOBERON) assemble $(OFRTH).py $(OFRTH).bin -s $(OFRTH).symbols -e ' $$afe ' -p > assembler.output.txt
