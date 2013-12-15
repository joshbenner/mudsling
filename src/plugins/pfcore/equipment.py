from collections import defaultdict

import mudsling.parsers
import mudsling.utils.string as str_utils

import pathfinder.equipment
import pathfinder.commands
import pathfinder.weapons
import pathfinder.combat


class Arrow(pathfinder.weapons.Ammunition):
    name = 'Arrow'


class ArrowBundle(pathfinder.equipment.Equipment):
    """
    A bundle of one type of arrows.

    .. todo:: Splitting bundles into other bundles.
    """
    arrow_type = Arrow
    arrow_count = 20

    def add_arrows(self, amount=1):
        """
        Add arrows to the bundle.
        """
        self.arrow_count += amount

    def remove_arrows(self, amount=1):
        """
        Remove arrows from the bundle.
        :returns: The number of arrows actually removed.
        :rtype: int
        """
        remove = min(self.arrow_count, amount)
        self.arrow_count -= remove
        return remove

    @property
    def names(self):
        names = super(ArrowBundle, self).names
        autoname = "Bundle of %d %s" % (
            self.arrow_count,
            str_utils.inflection.plural_noun(self.arrow_type.name.lower(),
                                             count=self.arrow_count)
        )
        names = (autoname,) + names
        return names


class Quiver(pathfinder.equipment.WearableEquipment):
    """
    A wearable arrow container.
    """
    arrow_capacity = 20

    #: :type: defaultdict of (Arrow, int)
    arrow_inventory = None

    body_regions = ('back',)
    layer_value = 5
    max_sublayers = 2

    def on_object_created(self):
        self.arrow_inventory = defaultdict(int)

    @property
    def names(self):
        names = list(super(Quiver, self).names)
        if names:
            names[0] += ' (%d)' % self.num_arrows()
        return names

    def num_arrows(self):
        """
        How many arrows are currently in the quiver.
        :rtype: int
        """
        return sum(self.arrow_inventory.itervalues())

    def available_arrow_slots(self):
        """
        How many more arrows can this quiver hold?
        :rtype: int
        """
        return self.arrow_capacity - self.num_arrows()

    def add_arrows(self, arrow_type, amount=1):
        """
        Add arrows to the quiver.

        :param arrow_type: The type of arrow to add.
        :type arrow_type: Arrow

        :param amount: How many arrows to add.
        :type amount: int

        :return: The number of arrows added.
        :rtype: int
        """
        amount = min(self.available_arrow_slots(), amount)
        if amount:
            self.arrow_inventory[arrow_type] += amount
        return amount

    def remove_arrows(self, arrow_type, amount=1):
        """
        Remove arrows from the quiver.

        :param arrow_type: The type of arrow to remove.
        :type arrow_type: Arrow

        :param amount: How many arrows to remove.
        :type amount: int

        :return: How many arrows were removed.
        :rtype: int
        """
        amount = min(self.arrow_inventory[arrow_type], amount)
        if amount:
            self.arrow_inventory[arrow_type] -= amount
        return amount

    class RefillCmd(pathfinder.commands.CombatCommand):
        """
        refill <quiver> with <bundle> [:<emote>]

        Refills a quiver with arrows from the bundle.
        """
        aliases = ('refill',)
        syntax = '<quiver> {with|from} <bundle>'
        arg_parsers = {
            'quiver': 'this',
            'bundle': mudsling.parsers.MatchObject(cls=ArrowBundle,
                                                   search_for='arrow bundle',
                                                   show=True)
        }
        default_emotes = [
            "refills $quiver with $bundle."
        ]
        action_cost = {'standard': 1, 'move': 1}
        combat_only = False

        def run(self, this, actor, args):
            """
            :type this: Quiver
            :type actor: pathfinder.characters.Character
            :type args: dict
            """
            #: :type: ArrowBundle
            bundle = args['bundle']
            num_arrows = min(this.available_arrow_slots(), bundle.arrow_count)
            num_arrows = bundle.remove_arrows(num_arrows)
            this.add_arrows(bundle.arrow_type, num_arrows)

    public_commands = [RefillCmd]
