"""
This is our Twistd entry point. You could also use the normal twistd script
and point it towards mudsling/server.py.
"""

from sys import argv
from twisted.scripts.twistd import run

argv[1:] = [
    '-y', 'mudsling/server.py'
]

run()
