title: Message Sequences
aliases: mail sequences, mail ranges, message ranges, message filters, mail filters

Some mail commands (such as @mail/list) accept a message sequence, which is an expression that selects a limited set of messages.

A message sequence has two optional parts: **set** and **filter**

## Sets

Sets designate a base list of messages.

* `<num>` -- A specific message by number.
* `<num>-<num>` -- A range of messages by number.
* `first` -- The first message.
* `last` -- The last message.
* `next` -- The first unread message.
* `unread` -- All unread messages.
* `all` -- All messages (the default if no set given).

## Filters

Filters further limit the messages selected by the set based on message attributes.

* `before:<date>` -- Messages before specified datetime.
* `after:<date>` -- Messages after specified datetime.
* `since:<date>` -- Messages on or after specified datetime.
* `until:<date>` -- Messages on or before specified datetime.
* `from:<player>` -- Messages from a specific player.
* `to:<player>` -- Messages to a specific player.
* `%from:<string>` -- Messages with _string_ in the 'from' header.
* `%to:<string>` -- Messages with _string_ in the 'to' header.
* `subject:<string>` -- Messages with _string_ in the subject header.
* `body:<string>` -- Messages with _string_ in the body.
* `first:<num>` -- The first _num_ messages in the set.
* `last:<num>` -- The last _num_ messages in the set.

## Example Sequences

* `100-$ from:charlie` -- Messages starting at 100 that are from Charlie.
* `unread before:today` -- Unread messages received before today.
* `subject:foo` -- All messages with 'foo' in the subject line.
* `body:bar` -- All messages with 'bar' in the body text.
