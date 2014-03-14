import mudsling.storage
import mudsling.commands
import mudsling.locks
import mudsling.errors
import mudsling.messages
import mudsling.parsers
import mudsling.objects

import mudslingcore.objects
import mudslingcore.senses as senses

isa_occupant = mudsling.locks.Lock('isa(furniture.FurnitureOccupant)')


class NoOccupancy(mudsling.errors.Error):
    pass


class NotOccupyingFurniture(mudsling.errors.Error):
    pass


class InvalidSurface(mudsling.errors.Error):
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


class FurnitureOccupant(mudslingcore.objects.Character):
    """
    A character that can sit/lay/recline on furniture.

    :ivar furniture: A reference to the furniture object currently occupied by
        this character.
    :type furniture: Furniture

    :ivar furniture_posture: The class describing the posture the character
        has while occupying the furniture.
    :type furniture_posture: Posture

    :ivar furniture_talk: Whether to restrict communication to the scope of
        the currently-occupied furniture or not.
    :type furniture_talk: bool
    """
    furniture = None
    furniture_posture = None
    furniture_talk = False

    def contents_name(self, viewer=None):
        name = super(FurnitureOccupant, self).contents_name(viewer=viewer)
        if self.furniture is not None:
            name = '%s (%s)' % (name, self.furniture_desc_to(viewer))
        return name

    def furniture_desc_to(self, who=None):
        """
        Get a string describing this character's furniture state.

        :param who: The observer.
        :type who: mudsling.objects.Object or None

        :rtype: str
        """
        name = (self.furniture.name if who is None
                else who.name_for(self.furniture))
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
            furniture.add_occupant(self.ref())
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
        furniture.remove_occupant(self)
        self.furniture = None
        self.furniture_posture = None
        self.furniture_talk = False
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
        super(FurnitureOccupant, self) \
            .before_object_moved(moving_from, moving_to, by=by, via=via)
        try:
            self.leave_furniture()
        except NotOccupyingFurniture:
            pass  # Quietly fail.

    def say(self, speech):
        if not self.furniture_talk:
            super(FurnitureOccupant, self).say(speech)
        else:
            if not isinstance(speech, senses.Speech):
                speech = senses.Speech(str(speech), origin=self.ref())
            self.furniture.msg_occupants(speech, exclude=(self.ref(),))
            self.tell('You say quietly, "{g', speech.content, '{n".')

    def emote(self, pose, sep=' ', prefix='', suffix='', show_name=True):
        if not self.furniture_talk:
            super(FurnitureOccupant, self).emote(pose, sep=sep, prefix=prefix,
                                                 suffix=suffix,
                                                 show_name=show_name)
        else:
            pose = senses.Sight(self._prepare_emote(pose, sep, prefix, suffix,
                                                    show_name))
            self.furniture.msg_occupants(pose)

    class PrivateTalkCmd(mudsling.commands.Command):
        """
        privatetalk [on|off]

        Display your private talk status, or set your private talk mode.
        """
        aliases = ('privatetalk', 'tabletalk')
        syntax = '[{on|off}]'
        lock = isa_occupant

        def run(self, this, actor, args):
            """
            :type this: FurnitureOccupant
            :type actor: FurnitureOccupant
            :type args: dict
            """
            if (actor.furniture is None
                    or actor.furniture.occupant_capacity < 2):
                raise self._err('Private talk is only available when '
                                'occupying a piece of furniture that can '
                                'accommodate more than one occupant.')
            mode = args.get('optset1', None)
            if mode == 'on':
                if actor.furniture_talk:
                    actor.tell('{yPrivate talk is already {gON{y.')
                else:
                    actor.furniture_talk = True
                    actor.tell('{gPrivate talk activated. Only others '
                               'occupying the same piece of furniture will '
                               'hear you.')
            elif mode == 'off':
                if not actor.furniture_talk:
                    actor.tell('{yPrivate talk is already {rOFF{y.')
                else:
                    actor.furniture_talk = False
                    actor.tell('{rPrivate talk is OFF. Everyone can hear you.')
            else:
                if actor.furniture_talk:
                    actor.tell('Private talk is {gON{n. Only others '
                               'occupying the same piece of furniture will '
                               'hear you.')
                else:
                    actor.tell('Private talk is {rOFF{n. Everyone in the '
                               'same room as you can hear you.')
                actor.tell(self.syntax_help())

    private_commands = [PrivateTalkCmd]


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
    surface = True

    occupants = []
    surface_objects = []

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
        #: :type: list of PlaceableObject
        self.surface_objects = []

    def before_object_moved(self, moving_from, moving_to, by=None, via=None):
        super(Furniture, self).before_object_moved(moving_from, moving_to,
                                                   by=by, via=via)
        for occupant in self.occupants:
            occupant.leave_furniture()
        for obj in self.surface_objects:
            obj.displace(by=by)

    def contents_name(self, viewer=None):
        name = super(Furniture, self).contents_name(viewer=viewer)
        if self.surface_objects:
            holding = ', '.join(o.contents_name(viewer=viewer)
                                for o in self.surface_objects)
            name = '%s (holding: %s)' % (name, holding)
        return name

    @property
    def available_occupancy(self):
        """:rtype: int"""
        return max(0, self.occupant_capacity - len(self.occupants))

    def add_occupant(self, occupant):
        self.occupants.append(occupant.ref())

    def remove_occupant(self, occupant):
        self.occupants.remove(occupant)

    def msg_occupants(self, msg, exclude=None):
        """
        Send a message to all occupants of this furniture.

        Based on mudsling.objects.Object.msg_contents

        :returns: List of objects to receive message.
        :rtype: list
        """
        # Offers caller freedom of not having to check for None, which he might
        # get back from some message generation calls.
        if msg is None:
            return []

        # Caller may have passed objects instead of references, but we need
        # references since we're doing 'in' matching against values in
        # contents, which really, really should be references.
        exclude = [e.ref() for e in (exclude or [])
                   if isinstance(e, mudsling.storage.StoredObject)
                   or isinstance(e, mudsling.storage.ObjRef)]

        if isinstance(msg, dict):
            # Dict keys indicate what objects receive special messages. All
            # others receive whatever's in '*'.
            _content = lambda o: msg[o] if o in msg else msg['*']
        else:
            _content = lambda o: msg

        if isinstance(msg, senses.Sensation):
            def _method(obj, content):
                if (obj.isa(senses.SensingObject)
                        and obj.has_any_sense(content.sensed_by)):
                    obj.sense(content)
                    return obj
        else:
            def _method(obj, content):
                obj.msg(content)

        receivers = []
        for o in self.occupants:
            if o in exclude or not o.is_valid(mudsling.objects.Object):
                continue
            receivers.append(_method(o, _content(o)))

        return filter(None, receivers)

    def add_to_surface(self, obj):
        """
        Add an object to this object's surface.

        This gets called by PlaceableObject.place_on(), so all we do here is
        modify our internal list of surface objects.

        :param obj: The object being placed on this object.
        :type obj: PlaceableObject
        """
        if obj not in self.surface_objects:
            self.surface_objects.append(obj.ref())

    def remove_from_surface(self, obj):
        """
        Remove an object from this object's surface.

        This gets called by PlaceableObject, so all we do is update internal
        list of surface objects.

        :param obj: The object to remove.
        """
        if obj in self.surface_objects:
            self.surface_objects.remove(obj)

    class FurnitureSitCmd(mudsling.commands.Command):
        """
        sit|lie|recline [down] on <furniture>

        Occupy a piece of furniture with the specified posture.
        """
        aliases = ('sit', 'lie', 'lay', 'recline')
        syntax = '[down] {on|in|at|across|upon|atop} \w <this>'
        lock = isa_occupant
        arg_parsers = {
            'this': 'this'
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
        arg_parsers = {'this': 'this'}
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
            'this': 'this'
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


class PlaceableObject(mudslingcore.objects.CoreObject):
    """
    An object that can be placed on a furniture surface.
    """
    placed_on = None

    messages = mudsling.messages.Messages({
        'displace': {
            'actor': 'You remove $this from $furniture.',
            '*': '$actor removes $this from $furniture.'
        },
        'place': {
            'actor': 'You place $this on $furniture.',
            '*': '$actor places $this on $furniture.'
        }
    })

    def show_in_contents_to(self, obj):
        show = super(PlaceableObject, self).show_in_contents_to(obj)
        return show and self.placed_on is None

    def place_on(self, furniture, by=None):
        """
        Place this object on a piece of furniture.

        :param furniture: The piece of furniture on which to place this.
        :type furniture: Furniture

        :param by: The object placing this on furniture.
        :type: by: mudsling.objects.Object

        :raises: InvalidSurface
        """
        if not (self.game.db.is_valid(furniture, Furniture)
                and furniture.surface):
            raise InvalidSurface('Invalid furniture surface')
        if self.location != furniture.location:
            self.move_to(furniture.location)
        if self.placed_on is not None:
            self.displace(by=by)
        furniture.add_to_surface(self)
        self.placed_on = furniture
        if self.game.db.is_valid(by, mudsling.objects.Object):
            self.emit_message('place', actor=by, furniture=furniture)

    def displace(self, by=None):
        """
        Remove this object from the furniture on which it rests.
        """
        furniture = self.placed_on
        self.placed_on = None
        if self.game.db.is_valid(furniture, Furniture):
            furniture.remove_from_surface(self)
            if self.game.db.is_valid(by, mudsling.objects.Object):
                self.emit_message('displace', actor=by, furniture=furniture)

    def before_object_moved(self, moved_from, moved_to, by=None, via=None):
        super(PlaceableObject, self).before_object_moved(moved_from, moved_to,
                                                         by=by, via=via)
        if self.placed_on is not None:
            self.displace(by=by)

    class FurniturePutCmd(mudsling.commands.Command):
        """
        put <object> on <furniture>

        Place an object on a furniture surface.
        """
        aliases = ('put', 'place', 'set')
        syntax = '<this> on <furniture>'
        arg_parsers = {
            'furniture': mudsling.parsers.MatchObject(Furniture, show=True,
                                                      search_for='furniture'),
            'this': 'this'
        }
        lock = mudsling.locks.all_pass

        def run(self, this, actor, args):
            """
            :type this: PlaceableObject
            :type actor: mudslingcore.objects.Character
            :type args: dict
            """
            #: :type: Furniture
            furniture = args['furniture']
            if this.placed_on == furniture:
                raise self._err('%s is already on %s.'
                                % (actor.name_for(this),
                                   actor.name_for(furniture)))
            this.place_on(furniture, by=actor)

    public_commands = [FurniturePutCmd]


class PlaceableThing(mudslingcore.objects.Thing, PlaceableObject):
    """
    A thing that can be placed on furniture surfaces.
    """


class Sofa(Furniture):
    occupant_capacity = 3


class Chair(Furniture):
    occupant_capacity = 1


class SmallTable(Furniture):
    occupant_capacity = 2


class MediumTable(Furniture):
    occupant_capacity = 4


class LargeTable(Furniture):
    occupant_capacity = 8


class Desk(Furniture):
    occupant_capacity = 1
