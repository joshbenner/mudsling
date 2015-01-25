title: Mail System
aliases: @mail

MUDSling's mail system allows players to send and receive messages to and from other players. The commands below may be used to view your inbox and send messages.

## Listing Messages
* `@mail` -- The main mail command. Defaults to /list.
* `@mail/list [<sequence>]` -- List messages in your inbox, matching optional [sequence](message sequences).
* `@mail/new` -- List new (unread) messages in your inbox.

## Reading Messages
* `@mail/read <message-num>` -- Read a specific message.
* `@mail/next` -- Read next unread message.

## Sending Messages
* `@mail/send <recipients>[=<subject>]` -- Open mail editor to compose a message.
* `@mail/reply <message-num>` -- Reply to message in mail editor.
* `@mail/forward <message-num> to <recipients>` -- Forward a message in the editor.

## Quick Commands
* `@mail/quick <recipients>[/<subject>]=<text>` -- Send a quick message.
* `@mail/quickrkeply <message-num>=<text>` -- Quick reply to a message.
* `@mail/quickforward <message-num> to <recipients>` -- Quick forward.

See also: [[message sequences]], [[mail editor]]
