import pathfinder.damage


class Bludgeoning(pathfinder.damage.DamageType):
    pass


class Piercing(pathfinder.damage.DamageType):
    pass


class Slashing(pathfinder.damage.DamageType):
    pass


class Force(pathfinder.damage.DamageType):
    pass


class Acid(pathfinder.damage.DamageType):
    kind = 'energy'


class Cold(pathfinder.damage.DamageType):
    kind = 'energy'


class Electricity(pathfinder.damage.DamageType):
    kind = 'energy'


class Fire(pathfinder.damage.DamageType):
    kind = 'energy'


class Sonic(pathfinder.damage.DamageType):
    kind = 'energy'
