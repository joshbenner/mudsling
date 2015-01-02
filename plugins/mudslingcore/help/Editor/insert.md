title: .insert (editor command)
aliases: .insert, insert, .i, .ins

Changes the current insertion point (or "caret") in the editor to the specified location.

When the insertion point is set, it is setting the line number of the next line that is added. So to insert text between lines 2 and 3, the new line would become the new line 3, so that is insertion point 3.

You can also specify a caret (^) or underscore (_) to indicate the insertion point should be before or after the indicated line number (respectively).

Syntax: `.insert [_|^] <line number>`

Note that, as an editor command, it does not require the space between the command and the arguments, so shorthand versions of the command are very succinct:

* `.i_2`
* `.i^10`
* `.i$`

See: [[editor]], [[line numbers]]
