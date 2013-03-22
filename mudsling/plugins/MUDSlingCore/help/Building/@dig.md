required_perm: use building commands

Syntax

* `@dig <new room>`                     -- Create a new room with no links.
* `@dig <exit spec> to <new room>`      -- Link current room to new room.
* `@dig <exit spec> to <existing room>` -- Link current room to existing room.

Exit spec syntax

* `<names>` -- Comma-separated list of names for the exit leaving.
* `<names>|<names>` -- Two comma-separated lists of names. The first is for the departing exit, and the second is the names for a new exit returning from the other room to the current room.

Examples

* `@dig My New Room`
* `@dig Out,o to #1234`
* `@dig In,i|Out,o to My New Room`
