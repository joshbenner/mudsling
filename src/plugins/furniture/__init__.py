import mudsling.storage
import mudsling.commands
import mudsling.locks
import mudsling.errors
import mudsling.messages
import mudsling.parsers

import mudslingcore.objects

isa_occupant = mudsling.locks.Lock('isa(furniture.FurnitureOccupant)')


class NoOccupancy(mudsling.errors.Error):
    pass


class NotOccupyingFurniture(mudsling.errors.Error):
    pass


class Posture(mudsling.storage.PersistentSlots):
    __slots__ = ('preposition',)

    base = ''        # You <base> on the sofa.
    participle = ''  # Joe is <participle> on the sofa.
    indicative = ''  # Joe <indicative> on the sofa.

    def __init__(self, prep='on'):
        self.preposition = prep


class Sitting(Posture):
    base = 'sit'
    participle = 'sitting'
    indicative = 'sits'


class Lying(Posture):
    base = 'lie'
    participle = 'lying'
    indicative = 'lies'


class Reclining(Posture):
    base = 'recline'
    participle = 'reclining'
    indicative = 'reclines'


class Furniture(mudslingcore.objects.Thing):
    """
    A piece of furniture which may be occupied by other objects.

    :cvar occupant_capacity: How many characters can occupy this furniture.
    :type occupant_capacity: int

    :cvar surface: Whether or not the furniture has a surface on which objects
        can be placed.
    :type surface: bool

    :ivar occupants: The character(s) occupying the furniture.
    :type occupants: list of FurnitureOccupant
    """
    occupant_capacity = 1
    surface = False

    occupants = []

    messages = mudsling.messages.Messages({
        'occupant added': {
            'actor': 'You ${posture.base} ${posture.preposition} $this.',
            '*': '$actor ${posture.indicative} ${posture.preposition} $this.'
        },
        'occupant left': {
            'actor': 'You stand up from ${posture.participle} '
                     '${posture.preposition} $this.',
            '*': '$actor stands up from ${posture.participle} '
                 '${posture.preposition} $this.'
        },
        'occupant shoved': {
            'actor': 'You shove $occupant away from $this.',
            'occupant': '$actor shoves you away from $this!',
            '*': '$actor shoves $occupant away from $this.'
        }
    })

    def on_object_created(self):
        #: :type: list of FurnitureOccupant
        self.occupants = []

    @property
    def available_occupancy(self):
        """:rtype: int"""
        return max(0, self.occupant_capacity - len(self.occupants))

    class FurnitureSitCmd(mudsling.commands.Command):
        """
        sit|lie|recline [down] on <furniture>

        Occupy a piece of furniture with the specified posture.
        """
        aliases = ('sit', 'lie', 'lay', 'recline')
        syntax = '[down] {on|in|at|across|upon|atop} \w <this>'
        lock = isa_occupant
        arg_parsers = {
            'this': 'THIS'
        }
        postures = {
            'sit': Sitting,
            'lie': Lying,
            'lay': Lying,
            'recline': Reclining
        }

        def run(self, this, actor, args):
            """
            :type this: Furniture
            :type actor: FurnitureOccupant
            :type args: dict
            """
            if actor.furniture is not None and actor.furniture != this:
                raise self._err('You are %s' % actor.furniture_desc_to(actor))
            posture_class = self.postures[self.cmdstr.lower()]
            posture = posture_class(prep=args['optset1'].lower())
            actor.occupy_furniture(this, posture)

    class FurnitureStandCmd(mudsling.commands.Command):
        """
        stand from <furniture>

        Stand up from occupying a piece of furniture.
        """
        aliases = ('stand', 'rise')
        syntax = 'from <this>'
        arg_parsers = {'this': 'THIS'}
        lock = isa_occupant

        def run(self, this, actor, args):
            """
            :type this: Furniture
            :type actor: FurnitureOccupant
            :type args: dict
            """
            if actor.furniture != this:
                raise self._err('You are not occupying %s'
                                % actor.name_for(this))
            actor.leave_furniture()

    class FurnitureShoveCmd(mudsling.commands.Command):
        """
        shove <character> from <furniture>

        Push a character off of the furniture.
        """
        aliases = ('shove', 'push')
        syntax = '<character> {from|off|off of|out of} <this>'
        arg_parsers = {
            'character': mudsling.parsers.MatchObject(FurnitureOccupant,
                                                      search_for='character',
                                                      show=True),
            'this': 'THIS'
        }
        lock = isa_occupant

        def run(self, this, actor, args):
            """
            :type this: Furniture
            :type actor: FurnitureOccupant
            :type args: dict
            """
            #: :type: FurnitureOccupant
            occupant = args['character']
            if occupant.furniture != this:
                raise self._err('%s is not occupying %s'
                                % (actor.name_for(occupant),
                                   actor.name_for(this)))
            occupant.shoved_from_furniture(by=actor)

    public_commands = [FurnitureSitCmd, FurnitureStandCmd, FurnitureShoveCmd]


class FurnitureOccupant(mudslingcore.objects.Character):
    """
    A character that can sit/lay/recline on furniture.

    :ivar furniture: A reference to the furniture object currently occupied by
        this character.
    :type furniture: Furniture

    :ivar furniture_posture: The class describing the posture the character
        has while occupying the furniture.
    :type furniture_posture: Posture
    """
    furniture = None
    furniture_posture = None

    def furniture_desc_to(self, who=None):
        """
        Get a string describing this character's furniture state.

        :param who: The observer.
        :type who: mudsling.objects.Object

        :rtype: str
        """
        name = self.name if who is None else who.name_for(self)
        return ' '.join((self.furniture_posture.participle,
                         self.furniture_posture.preposition,
                         name))

    def occupy_furniture(self, furniture, posture):
        """
        Begin occupying a piece of furniture.

        :param furniture: The furniture object to occupy.
        :type furniture: Furniture

        :param posture: The posture with which to occupy the furniture.
        :type posture: Posture

        :raises: NoOccupancy
        """
        if self.furniture == furniture:
            # Already occupying furniture, so we're just changing posture.
            self.furniture_posture = posture
        else:
            if furniture.available_occupancy < 1:
                raise NoOccupancy('%s is occupied' % self.name_for(furniture))
            if self.furniture is not None:
                self.leave_furniture()
            self.furniture = furniture
            self.furniture_posture = posture
        furniture.emit_message('occupant added', actor=self.ref(),
                               posture=posture)

    def leave_furniture(self, stealth=False):
        """
        Cease occupying the currently-occupied piece of furniture.

        :raises: NotOccupyingFurniture
        """
        if self.furniture is None:
            raise NotOccupyingFurniture('Not occupying any furniture')
        furniture = self.furniture
        posture = self.furniture_posture
        self.furniture = None
        self.furniture_posture = None
        if not stealth:
            furniture.emit_message('occupant left', actor=self.ref(),
                                   posture=posture)

    def shoved_from_furniture(self, by):
        """
        This character is shoved out of their current furniture occupancy.

        :param by: The object shoving them out.
        :type by: FurnitureOccupant
        """
        furniture = self.furniture
        posture = self.furniture_posture
        self.leave_furniture(stealth=True)
        furniture.emit_message('occupant shoved', actor=by,
                               occupant=self.ref(), posture=posture)

    def before_object_moved(self, moving_from, moving_to, by=None, via=None):
        super(FurnitureOccupant, self)\
            .before_object_moved(moving_from, moving_to, by=by, via=via)
        try:
            self.leave_furniture()
        except NotOccupyingFurniture:
            pass  # Quietly fail.


class Sofa(Furniture):
    occupant_capacity = 3


class Chair(Furniture):
    occupant_capacity = 1
