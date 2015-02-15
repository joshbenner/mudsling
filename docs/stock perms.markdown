This is documentation for the stock permissions that MUDSling and mudslingcore
use for core or system functionality.

MUDSling System
---------------
* see object numbers

mudslingcore
------------
* shutdown server
* reload server
* eval code
* manage tasks
* view perms
* manage roles
* grant roles
* create things -- Player may create objects of class Thing.
* create objects
* delete objects
* configure own objects
* configure all objects
* use building commands
* remote look -- Look at objects outside of own context.
* teleport -- Player may access teleportation commands.
* create players -- Player may create other players.
* manage players -- Change other players' passwords.
* boot players -- Disconnect other players.
* shout -- Can shout.
* ban -- Can ban players and IP addresses.
* create channels -- Can create new channel objects via +chancreate.
* delete channels -- Can delete channels via +chandel.
* join any channel -- Can join any channel, even private channels.
* global operator -- Operator on all channels.
* inspect objects -- @show any object.
* import areas -- Can import area files.
* export areas -- Can export areas to JSON.
* use mail -- Can use @mail commands.
* script anything -- Script any object
* use nested matching -- Can use '->' to match nested objects when literal matching is used.
* use global vars -- Can use '$'-prefixed objects for matching.

## Object Lock types
* control
* rename
* delete
* move
* script
