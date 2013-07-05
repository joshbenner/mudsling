from mudsling.utils.object import AttributeAlias, ClassProperty


class Gender(object):
    subject = ''
    object = ''
    reflexive = ''
    possessive_determiner = ''
    possessive_pronoun = ''

    # noinspection PyNestedDecorators
    @ClassProperty
    @classmethod
    def name(cls):
        return cls.__name__

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


genders = {
    'neuter': Neuter,
    'male': Male,
    'female': Female,
    'spivak': Spivak,
}
