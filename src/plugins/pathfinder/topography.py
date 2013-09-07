import mudsling.utils.string

import mudslingcore.topography

import pathfinder.combat


class Room(mudslingcore.topography.Room, pathfinder.combat.Battleground):
    """
    A room which allows combat.
    """

    def leave_allowed(self, what, exit=None):
        if what.isa(pathfinder.combat.Combatant) and what.in_combat:
            what.tell('{rYou must leave combat to leave the room.')
            return False
        return super(Room, self).leave_allowed(what, exit=exit)

    def after_content_added(self, what, previous_location, by=None, via=None):
        super(Room, self).after_content_added(what, previous_location, by, via)
        if what.isa(pathfinder.combat.Combatant):
            if via.isa(mudslingcore.topography.Exit):
                pos = via.counterpart or self.ref()
            else:
                pos = self.ref()
            if what.combat_position != pos:
                what.combat_move(pos, stealth=True)

    def combat_areas(self, exclude_self=False):
        areas = super(Room, self).combat_areas(exclude_self=exclude_self)
        areas.extend(self.exits)
        return areas

    def adjacent_combat_areas(self, area):
        adjacent = super(Room, self).adjacent_combat_areas(area)
        if area == self or area == self.ref():
            adjacent.extend(self.exits)
        return adjacent

    def combatants(self):
        """
        :rtype: list of pathfinder.combat.Combatant
        """
        return [c for c in self.contents if c.isa(pathfinder.combat.Combatant)]

    def contents_as_seen_by(self, obj):
        """
        Return the contents of the room as seen by the passed object.
        """
        lines = []
        combatants = [c for c in self.combatants() if c != obj]
        contents = [c for c in self.contents
                    if c not in combatants and c != obj]
        if obj.isa(pathfinder.combat.Combatant):
            desc = lambda c: obj.combat_position_desc(c.combat_position)
        else:
            desc = lambda c: ('in the open' if c.combat_position == self
                              else "near %s" % obj.name_for(c.combat_position))
        if combatants:
            lines.append('You see:')
            for combatant in combatants:
                name = obj.name_for(combatant)
                pos = desc(combatant)
                if combatant.combat_position == obj:
                    pos = '{r' + pos.upper()
                status = '{rFIGHTING' if combatant.in_combat else ''
                lines.append('  {m%s{n ({c%s{n) %s' % (name, pos, status))
        if contents:
            fmt = "{c%s{n"
            if self.game.db.is_valid(obj):
                def name(o):
                    return fmt % obj.name_for(o)
            else:
                def name(o):
                    return fmt % o.name
            names = mudsling.utils.string.english_list(map(name, contents))
            if combatants:
                lines.append('')
                lines.append("You also see: %s" % names)
            else:
                lines.append("You see: %s" % names)
        return '\n'.join(lines)
