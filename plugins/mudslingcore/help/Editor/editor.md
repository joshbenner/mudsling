title: Line Editor
aliases: editor, line editor, editing text, text editor

MUDSling's line editor allows users to edit multi-line text, such as descriptions or messages. While editing text using an applicaton on your computer and pasting it in is often better, the editor offers you an alternative that is located entirely in-game.

## Initiating an Editor Session

* `@edit <object>.<setting>` - Edit a string object setting.
* `@desc <object>` - Edit the object's 'desc' setting (same as typing `@edit <object>.desc`).

These commands have more options, which can be found in their help files.

## Managing Editor Sessions

You may have multiple editor sessions opened at one time, just like having multiple tabs open in a browser. And just like only one tab in a window can be shown at a time, only one editor session can be *active* at a time.

* `@editors` - Show a list of open editors.
* `@switch-editor <session number>|OFF` - Switch to an open editor, or none.

## Editor Commands

You may have more or less commands available, depending on which kind of data you are editing. This list comprises the most common commands for manipulating text.

Inserting a new line of text is done by typing the single quote (') character, followed by the text to insert. No space is needed between the single quote and the text to insert.

* [[`.what`]]
* [[`.abort`]], [[`.done`]]
* [[`.save`]]
* [[`.enter`]], [[`.paste`]]
* [[`.insert`]]
* [[`.delete`]]
* [[`.list`]], [[`.print`]]
* [[`.replace`]], [[`.subst`]]
