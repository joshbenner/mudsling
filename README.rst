MUDSling is a MUD engine written in Python_ and powered by Twisted_.

.. _Python: http://python.org
.. _Twisted: http://twistedmatrix.com

Base Engine Features
====================

* Long-running task API
* Lock language
* Extensible parser objects
* Permissions system
* Plugin system
* Secure password storage (PBKDF2)
* Straightforward command authoring with sophisticated syntax parser
* Comprehensive utilities package (strings, time, files, units, sequences, and so on)
* Optional proxy
* ANSI256
* MXP

Bundled Plugins
===============

MUDSling also includes several bundled plugins:

* **MUDSling Core**
    + Base set of game commands
    + UI system
    + Import/export JSON area files
    + Help system
    + Gender system
    + Global object system
    + IP Banning
    + Line editor
    + Object Settings system
    + Senses (sight, sound)
    + Building: Rooms/exits
* **My Objects**: personal global objects
* **Dice**: Comprehensive dice rolling system and language
* **Furniture**: Interactive furniture objects
* **IC Money**: Dynamic money system with arbitrary currency denominations and exchanges
* **IC Time**: Custom calendars for your game world
* **Default Login Screen**: A start for your own login screen
* **Organizations**: Multi-membership, rank-based organization hierarchies
* **REST Server**: Simple, authenticated REST API framework
* **Wearables**: Clothing objects that can overlap hold objects
* **Simple Telnet Server**: Alternative to proxy to allow direct connections to game server

Getting Started
===============

.. sourcecode:: console

    $ hg clone https://bitbucket.org/joshbenner/mudsling
    $ cd mudsling
    $ pip install -r requirements.txt
    $ python run.py

Then you may connect to localhost:4000 with your MUD client.