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
