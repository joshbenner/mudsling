import mudsling.utils.sequence
import mudsling.pickler
import mudsling.utils.units as units

materials = mudsling.utils.sequence.CaselessDict()


class Material(object):
    __slots__ = ('name', 'hardness', 'hp_per_inch', 'density')

    def __new__(cls, name, hardness=None, hp_per_inch=None, density=None):
        if name in materials:
            material = materials[name]
        else:
            material = super(Material, cls).__new__(cls)
            material.name = name
            materials[name] = material
        if hardness is not None:
            material.hardness = hardness
        if hp_per_inch is not None:
            material.hp_per_inch = hp_per_inch
        if density is not None:
            material.density = density
        return material

#    def weight(self, dimensions):



mudsling.pickler.register_external_type(
    Material,
    persistent_id=lambda m: m.name.lower(),
    persistent_load=Material
)


# Declare some default Materials:
kgpm3 = units.kg / units.meter ** 3
glass = Material('Glass', hardness=1, hp_per_inch=1, density=2400 * kgpm3)
paper = Material('Paper', 0, 2, 700 * kgpm3)
cloth = Material('Cloth', 0, 2, 600 * kgpm3)
rope = Material('Rope', 0, 2, 1300 * kgpm3)
ice = Material('Ice', 0, 3, 917 * kgpm3)
leather = Material('Leather', 2, 5, 860 * kgpm3)
hide = Material('Hide', 2, 5, 885 * kgpm3)
wood = Material('Wood', 5, 10, 700 * kgpm3)
stone = Material('Stone', 8, 15, 2500 * kgpm3)
iron = Material('Iron', 10, 30, 7870 * kgpm3)
steel = Material('Steel', 10, 30, 7820 * kgpm3)
mithral = Material('Mithral', 15, 30, 1200 * kgpm3)
mithril = mithral
adamantine = Material('Adamantine', 20, 40, 7500 * kgpm3)
adamant = adamantine
adamantium = adamantine
