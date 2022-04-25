# -*- coding: utf-8 -*-
#
#    Copyright © 2019 Simon Forman
#
#    This file is part of PythonOberon
#
#    PythonOberon is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    PythonOberon is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with PythonOberon.  If not see <http://www.gnu.org/licenses/>.
#
'''
Use the demo module to fire up the system,
Load disk and (optionally) image over serial port.
Run for eight million cycles.
'''
from argparse import ArgumentParser, FileType
from pkg_resources import resource_filename


parser = ArgumentParser(
    prog='python -m oberon',
    #usage='python -i -m oberon [-d DISK_IMAGE]',
    description='An emulator for Prof Wirth\'s RISC CPU for Project Oberon.',
    )

subparsers = parser.add_subparsers(help='sub-command help')

asm_subparser = subparsers.add_parser('assemble')

asm_subparser.add_argument(
    'source',
    type=FileType('rb'),
    )
asm_subparser.add_argument(
    'output',
    type=FileType('wb'),
    )
asm_subparser.add_argument(
    '-s', '--symbol-file',
    type=FileType('wb'),
    )
asm_subparser.add_argument(
    '-p', '--print-program',
    action='store_true',
    )
asm_subparser.add_argument(
    '-e', '--epilog',
    )
asm_subparser.add_argument(
    '-a', '--additional-data',
    type=FileType('rb'),
    )

emu_subparser= subparsers.add_parser('emulate')

emu_subparser.add_argument(
    '-d', '--disk-image',
    type=FileType('rb'),
    default=resource_filename(__name__, 'disk.img'),
    )
emu_subparser.add_argument(
    '--serial-in',
    type=FileType('rb'),
    )

args = parser.parse_args()

if hasattr(args, 'output'):  # We are assembling
    from oberon.assembler import assemble_file

    epilog = args.epilog.encode('UTF_8') if args.epilog else None

    assemble_file(
        args.source,
        args.output,
        args.symbol_file,
        print_program=args.print_program,
        additional_data=args.additional_data,
        epilog=epilog,
        )

else:  # We are emulating.

    # Do not import this unless we need to, because pygame
    # prints a banner when imported.  This way you can use
    # the '-h' options without the clutter of the banner, yet
    # still see it when starting the program proper.
    from oberon.demo import cycle, make_cpu

    print(('Using disk image file', args.disk_image.name))
    cpu = make_cpu(args.disk_image, args.serial_in)
    # Details begin to be painted around 6.5M cycles.
    cycle(cpu, 8000000)
