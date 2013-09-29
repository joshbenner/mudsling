from .characters import CharacterFeature
import pathfinder.errors as pferr


class Feat(CharacterFeature):
    """
    A feat.

    Instances represent the possession of the feat. So, when a character gains
    a feat, an instance of that feat is stored on the character. This allows
    some feats to have feat subtypes (ie: which weapon for Weapon Focus).
    """
    __slots__ = ('subtype', 'sources', 'slot')

    feature_type = 'feat'
    name = ''
    type = 'general'
    restricted = False  # Only available if a slot with specific type is free.
    multiple = False
    _prerequisites = []
    modifiers = []

    @classmethod
    def subtypes(cls):
        """Get the list of subtypes available.

        :return: A case-insensitive dict of strings subtype names as keys, and
            the data to store on the feat instance as value.
        :rtype: mudsling.utils.sequence.CaselessDict
        """
        return {}

    @classmethod
    def canonical_subtype(cls, subtype):
        """Return the case-correct name of the given subtype.

        :param subtype: The subtype to canonicalize.
        :type subtype: str

        :returns: A case-correct name of a subtype.
        :rtype: str
        """
        return cls.subtypes().canonical_key(subtype)

    @classmethod
    def canonical_name(cls, subtype=None):
        name = cls.name
        if subtype is not None:
            name += " (%s)" % cls.canonical_subtype(subtype)
        return name

    @classmethod
    def prerequisites(cls, subtype=None):
        prerequisites = []
        for req in cls._prerequisites:
            if 'same subtype' in req and subtype is not None:
                req = req.replace('same subtype', subtype)
            prerequisites.append(req)
        return prerequisites

    @classmethod
    def compatible_slots(cls, subtype=None):
        if cls.restricted:
            return cls.type,
        elif cls.type == 'general':
            return 'general',
        else:
            return 'general', cls.type

    def __init__(self, subtype=None, source=None, slot=None):
        subtypes = self.subtypes()
        if ((len(subtypes) and subtype not in subtypes)
                or (not len(subtypes) and subtype is not None)):
            msg = "Invalid subtype (%s) for Feat %s" % (subtype, self.name)
            raise pferr.InvalidSubtype(msg, self, subtype)
        if subtype is not None:
            subtype = self.canonical_subtype(subtype)
        self.subtype = subtype
        self.sources = []
        self.slot = slot
        if source is not None:
            self.sources.append(source)
        if slot is not None and 'slot' not in self.sources:
            self.sources.append('slot')

    def __str__(self):
        if self.multiple:
            return "%s (%s)" % (self.name, self.subtype)
        else:
            return super(Feat, self).__str__()

    def __repr__(self):
        return 'Feat: %s' % str(self)
