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

Read bytes from UART and send them on SPI.

*/

#define F_CPU 1000000UL	// Factory default frequency ~1MHz
#define BAUD 2400
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/sleep.h>
#include <util/setbaud.h>


// When a byte is received send it over SPI.
ISR(USART_RX_vect) {
  uint8_t y = UDR0;
  PORTD = y;  // Diagnostic.
  SPDR = y;
}


static void init_uart_2400(void) {
	UBRR0H = UBRRH_VALUE;  // Baud rate calculated by the header (neat!)
	UBRR0L = UBRRL_VALUE;
	UCSR0A &= ~(1 << U2X0);  // Don't use double speed (I think.)
	UCSR0B = (1 << TXEN0) | (1 << RXEN0); // Enable transmit/receive
	// The chip defaults to 8N1 so we won't set it here even though we should.
	UCSR0B |= (1 << RXCIE0);  // Receive Complete Interrupt Enable.
}


int main(void) {

	// Set up the I/O ports.
	DDRB = 0; PORTB = 0xFF;
	DDRC = 0; PORTC = 0x7F;
	//DDRD = 0; PORTD = 0xFF;

	// Activate Port D as output and display a pattern to so "Hi".
  // 13.2.3 Switching Between Input and Output (datasheet)
  PORTD = 0x00;
	DDRD = 0xFF;
  PORTD = 0x33;

  PORTB &= ~(_BV(PORTB3) | _BV(PORTB5));  // Clear port bits.
  DDRB = _BV(PORTB3) | _BV(PORTB5);  // Set MOSI & SCK to output.
  SPCR = _BV(SPE) | _BV(MSTR) ;  // Turn on SPI.

  init_uart_2400();
	// Set sleep mode, enable interrupts and sleep, enter mainloop.
	set_sleep_mode(SLEEP_MODE_IDLE);
	sei();
	sleep_enable();
	while (1) {
		sleep_cpu();
    // SPI will continue while we sleep.
	}

	return 0;
}
