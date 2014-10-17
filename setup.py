#!/usr/bin/env python

import os
from setuptools import setup

version_file = open(os.path.join(os.path.dirname(__file__), 'VERSION'))
version = version_file.read().strip()
version_file.close()
del version_file

setup(
    name='MUDSling',
    version=version,
    description='Python MUD engine',
    author='Joshua Benner',
    author_email='josh@bennerweb.com',
    url='https://bitbucket.org/joshbenner/mudsling',
    license='GPLv2',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Framework :: Twisted',
        'Environment :: Web Environment',
        'License: GNU General Public License v2 (GPLv2)',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Topic :: Games/Entertainment :: Multi-User Dungeons (MUD)',
    ],
    packages=['mudsling'],
    install_requires=[
        'pyparsing>=1.5',
        'twisted>=12',
        'markdown>=2.2',
        'psutil>=0.6',
        'inflect>=0.2',
        'fuzzywuzzy>=0.1',
        'pytz',
        'flufl.enum>=4',
        'python-dateutil>=2.1',
        'yoyo-migrations>=4.2.2',
        'pint>=0.5.2',
        'mailer',
        'simple-pbkdf2',
        'corepost'
    ],
    entry_points={
        'console_scripts': [
            'mudsling = runner:run'
        ]
    }
)
