/*

	Copyright © 2022 Simon Forman

	This file is part of PythonOberon.

	PythonOberon is free software: you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation, either version 3 of the License, or
	(at your option) any later version.

	PythonOberon is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU General Public License for more details.

	You should have received a copy of the GNU General Public License
	along with PythonOberon.  If not see <http://www.gnu.org/licenses/>.

A very simple serial<->parallel adaptor, using SPI.

Waits for an address over SPI and puts it on Port C, then a byte of data
which it puts on Port D.

For now it only handles output from the CPU to RAM.  There is no RAM yet
so there's no point in reading from it yet.

*/

#define F_CPU 1000000UL	// Factory default frequency ~1MHz
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/sleep.h>



ISR(SPI_STC_vect) {
  // https://electronics.stackexchange.com/questions/107146/avr-spi-target-with-interrupt/357274#357274
  // Dunno why you need to put it into a vaiable?
  // Cannot you just do PORTD = SPDR;?
  uint8_t y = SPDR;
  PORTD = y;
}


int main(void) {

	// Set up the I/O ports.

	// Activate Port D as output and display a pattern to so "Hi".
  // 13.2.3 Switching Between Input and Output (datasheet)
  PORTD = 0x00;
	DDRD = 0xFF;
  PORTD = 0x33;

  // For now park these ports.
	DDRB = 0; PORTB = 0xFF;
	DDRC = 0; PORTC = 0x7F;

  
  // Turn on SPI (interrupts and enable.)
  SPCR = _BV(SPIE) | _BV(SPE) ;

  // "Since it is not mandatory to send data back, the MISO channel can be configured either as output or input."
  // https://ww1.microchip.com/downloads/en/Appnotes/TB3215-Getting-Started-with-SPI-90003215A.pdf

  
	// Set sleep mode, enable interrupts and sleep, enter mainloop.
	set_sleep_mode(SLEEP_MODE_IDLE);
	sei();
	sleep_enable();
	while (1) {
		sleep_cpu();
	}

	return 0;
}
