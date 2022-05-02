CC=/usr/local/bin/avr-gcc
MEGA=328p
CFLAGS=-g -Os -Wall -mcall-prologues -mmcu=atmega$(MEGA)
OBJ2HEX=/usr/local/bin/avr-objcopy 
PROG=/usr/local/bin/avrdude

TARGET=orex
PORT=/dev/ttyU0

program : $(TARGET).hex
	$(PROG) -c avrispv2 -p m$(MEGA) -P $(PORT) -e
	$(PROG) -c avrispv2 -p m$(MEGA) -P $(PORT) -U flash:w:$(TARGET).hex

%.obj : %.o
	$(CC) $(CFLAGS) $< -o $@

%.elf : %.o
	$(CC) $(CFLAGS) $< -o $@

%.hex : %.obj
	$(OBJ2HEX) -R .eeprom -O ihex $< $@

clean :
	rm -f *.hex *.obj *.o
