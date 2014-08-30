from mudsling.utils.object import AttributeAlias, ClassProperty
import mudsling.messages
import mudsling.errors


class InvalidPronoun(mudsling.errors.Error):
    pass


class Gender(object):
    subject = ''
    object = ''
    reflexive = ''
    possessive_determiner = ''
    possessive_pronoun = ''
    valid_pronouns = {
        'subject': 'subject',
        'subjective': 'subject',
        'he_she': 'subject',
        'she_he': 'subject',
        'ey': 'subject',

        'object': 'object',
        'objective': 'object',
        'him_her': 'object',
        'her_him': 'object',
        'em': 'object',

        'reflex': 'reflexive',
        'reflexive': 'reflexive',
        'himself_herself': 'reflexive',
        'herself_himself': 'reflexive',
        'emself': 'reflexive',

        'possessive_determiner': 'possessive_determiner',
        'his_her': 'possessive_determiner',
        'her_his': 'possessive_determiner',
        'eir': 'possessive_determiner',

        'possessive_pronoun': 'possessive_pronoun',
        'his_hers': 'possessive_pronoun',
        'hers_his': 'possessive_pronoun',
        'eirs': 'possessive_pronoun',
    }

    # noinspection PyNestedDecorators
    @ClassProperty
    @classmethod
    def name(cls):
        return cls.__name__

    @classmethod
    def get_pronoun(cls, type):
        attr = cls.valid_pronouns.get(type, None)
        if attr is None:
            raise InvalidPronoun("No pronoun: %r" % type)
        return getattr(cls, attr)

    he_she = AttributeAlias('subject')
    she_he = he_she
    ey = he_she

    him_her = AttributeAlias('object')
    her_him = him_her
    em = him_her

    himself_herself = AttributeAlias('reflexive')
    herself_himself = himself_herself
    emself = himself_herself

    his_her = AttributeAlias('possessive_determiner')
    her_his = his_her
    eir = his_her

    his_hers = AttributeAlias('possessive_pronoun')
    hers_his = his_hers
    eirs = his_hers


class Neuter(Gender):
    subject = 'it'
    object = 'it'
    reflexive = 'itself'
    possessive_determiner = 'its'
    possessive_pronoun = 'its'


class Male(Gender):
    subject = 'he'
    object = 'him'
    reflexive = 'himself'
    possessive_determiner = 'his'
    possessive_pronoun = 'his'


class Female(Gender):
    subject = 'she'
    object = 'her'
    reflexive = 'herself'
    possessive_determiner = 'her'
    possessive_pronoun = 'hers'


class Spivak(Gender):
    subject = 'ey'
    object = 'em'
    reflexive = 'emself'
    possessive_determiner = 'eir'
    possessive_pronoun = 'eirs'


class HasGender(object):
    """An object with gender.
    :ivar gender: The object's gender.
    :type gender: Gender
    """
    gender = Neuter

    def get_pronoun(self, type):
        return self.gender.get_pronoun(type)

    class _gender_proxy(AttributeAlias):
        """Pass-thru to the gender class."""
        def __get__(self, obj, objtype=None):
            g = super(HasGender._gender_proxy, self).__get__(None, obj.gender)
            return g

        def __set__(self, obj, value):
            raise AttributeError("Attribute is read-only.")

        def __delete__(self, obj):
            raise AttributeError("Attribute is read-only.")

    he_she = _gender_proxy('subject')
    she_he = he_she
    ey = he_she

    him_her = _gender_proxy('object')
    her_him = him_her
    em = him_her

    himself_herself = _gender_proxy('reflexive')
    herself_himself = himself_herself
    emself = himself_herself

    his_her = _gender_proxy('possessive_determiner')
    her_his = his_her
    eir = his_her

    his_hers = _gender_proxy('possessive_pronoun')
    hers_his = his_hers
    eirs = his_hers


genders = {
    'neuter': Neuter,
    'male': Male,
    'female': Female,
    'spivak': Spivak,
}
