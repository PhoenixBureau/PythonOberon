#!/usr/bin/env python
import setuptools


with open("README.md", "r") as fh:
    long_description = fh.read()


setuptools.setup(
    name='PythonOberon',
    version='0.1.0',
    author='Simon Forman',
    author_email='sforman@hushmail.com',
    description='A hardware emulator for the Oberon RISC processor.',
    license='GPLv3+',
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=['oberon'],
    package_data={'oberon': ['disk.img']},
    url='https://git.sr.ht/~sforman/PythonOberon',
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: OS Independent',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Assemblers',
        'Topic :: Software Development :: Libraries :: pygame',
        'Topic :: System :: Emulators',
    ],
)
