from collections import OrderedDict
from mudsling import parsers
from mudsling.objects import BaseObject
from mudsling.utils import string as str_utils
from mudslingcore import ui


class InspectableObject(BaseObject, ui.UsesUI):
    """
    Basic object that can be used with @show.
    """

    def inspectable_ui(self, who=None):
        try:
            ui = who.get_ui()
        except AttributeError:
            ui = self.get_ui()
        return ui

    def inspectable_name(self, who=None):
        if self.game.db.is_valid(who, BaseObject):
            N = who.name_for
        else:
            N = lambda o: o.name
        return N

    def inspectable_callbacks(self, who=None):
        """
        Get a list of inspection headings and the callback to provide their
        content.
        """
        return [(None, self.format_inspectable_details, -1000)]

    def inspectable_details(self, who=None):
        """
        Key/value pairs to display when someone uses @show to inspect this.

        :param who: The object inspecting this object.
        """
        N = self.inspectable_name(who=who)
        details = OrderedDict((
            ('Names', ', '.join(self.names)),
            ('Class', parsers.ObjClassStaticParser.unparse(self.__class__)),
            ('Owner', N(self.owner))
        ))
        return details

    def format_inspectable_details(self, who=None):
        ui = self.inspectable_ui(who=who)
        tbl = ui.keyval_table(self.inspectable_details(who=who).items())
        return str_utils.columnize(str(tbl).splitlines(), 2,
                                   width=ui.table_settings['width'])

    def inspectable_output(self, who=None):
        callbacks = sorted(self.inspectable_callbacks(who=who),
                           key=lambda c: c[2])
        ui = self.inspectable_ui(who=who)
        sections = []
        for heading, callback, weight in callbacks:
            section = (ui.h2(heading) + '\n') if heading else ''
            section += callback(who=who)
            sections.append(section)
        return '\n\n'.join(sections)
