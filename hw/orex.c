/*

	Copyright © 2019 Simon Forman

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


This program drives an RGB LED in a simple pattern of random-seeming
colors.  It uses a timer interrupt to let the CPU stay mostly idle.

The timer is set to wake up the CPU ten times per second (10Hz) and each
LED in the RGB LED has its own blink period.  The periods are determined
by small prime numbers to give a long cycle time before the color pattern
repeats.

The periods, in tenths of a second, are 17, 23, and 39, so the total
cycle time is:

	17 * 39 * 23 = 15249

Or 1524.9 seconds.  Round up to 1525 and divide by 60 seconds in a minute
and you get a period of about 25.4 minutes.  Since the periods are odd
numbers the LEDs start the next cycle in the opposite state (on if they
were off, off if they were on) so the actual cycle time (before the
pattern repeats) is doubled, about 50.8 minutes.  Not bad, eh?


The factory default frequency of the ATmega328P is (close to) 1MHz. (It's
really 8MHz with a default divide-by-eight.)  If the timer prescaler is
set to divide the clock by 1024 we get a frequency of

	1000000Hz / 1024 = 976.5625Hz

This gives a clock tick duration of (unsurpisingly) 0.001024 seconds.  To
get a LED counter update tick of one tenth of a second we should count up

	0.1 / 0.001024 = 97.65625

Round up to 98 clock cycles per LED counter update tick.

*/

#define F_CPU 1000000UL	// Factory default frequency ~1MHz
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/sleep.h>

// #include <avr/iom328p.h>  // Supreswarns

// Get a nice long cycle by using prime numbers for the individual LEDs.
#define RED_CYCLE 17
#define GREEN_CYCLE 39
#define BLUE_CYCLE 23

// Pin masks for the output port toggling.
#define RED (1 << PORTD5)
#define GREEN (1 << PORTD6)
#define BLUE (1 << PORTD7)


// We just need the timer to wake us up.
EMPTY_INTERRUPT(TIMER0_COMPA_vect)


void update_LEDs(void) {

	// One counter for each LED and a mask to keep track of which LEDs
	// will toggle each cycle.
	static uint8_t red=0, green=0, blue=0, pins=0;

	if (red++ > RED_CYCLE) {
		red = 0;
		pins |= RED;
	}
	if (green++ > GREEN_CYCLE) {
		green = 0;
		pins |= GREEN;
	}
	if (blue++ > BLUE_CYCLE) {
		blue = 0;
		pins |= BLUE;
	}
	if (pins) {
		PORTD ^= pins;  // Toggle the LEDs if any.
		pins = 0;
	}
}


int main(void) {

	// Set up the I/O ports.

	// Activate the internal pull-up resistors on all ports.  This
	// protects the unconnected pins from stray noise and keeps power low.
	DDRB = 0; PORTB = 0xFF;
	DDRC = 0; PORTC = 0x7F;
	DDRD = 0; PORTD = 0xFF;

	// Port D pins 5/6/7 (R/G/B) to output mode.
	DDRD |= _BV(DDD5) | _BV(DDD6) | _BV(DDD7);

	// Set up timer frequency and interrupt.

	// Set timer prescaler to F_CPU / 1024 ~= 977Hz
	TCCR0B = _BV(CS00) | _BV(CS02);

	// 0.001024s * 98 = 0.100352s  Close enough to 1/10th of a second.
	OCR0A = 98;

	// Set Clear Timer on Compare Match (CTC) Mode
	TCCR0A = _BV(WGM01);

	// Enable timer interrupt.
	TIMSK0 |= _BV(OCIE0A);

	// Set sleep mode, enable interrupts and sleep, enter mainloop.
	set_sleep_mode(SLEEP_MODE_IDLE);
	sei();
	sleep_enable();
	while (1) {
		sleep_cpu();
		update_LEDs();
	}

	return 0;
}
