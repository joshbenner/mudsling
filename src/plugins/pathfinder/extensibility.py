import mudsling.extensibility
import mudsling.utils.modules

import pathfinder.languages
import pathfinder.races
import pathfinder.skills  # Skills must come before feats.
import pathfinder.feats
import pathfinder.special_abilities
import pathfinder.conditions
import pathfinder.classes
import pathfinder.data
import pathfinder.enhancements


class PathfinderPlugin(mudsling.extensibility.GamePlugin):
    """
    Plugins of this type can provide Pathfinder data. Technically, any
    GamePlugin instance may provide Pathfinder data, but this class makes it a
    little easier.
    """

    #: The submodule names mapped to the class whose children are registered in
    #: the pathfinder database.
    data_mapping = {
        'languages': pathfinder.languages.Language,
        'races': pathfinder.races.Race,
        'skills': pathfinder.skills.Skill,
        'feats': pathfinder.feats.Feat,
        'special_abilities': pathfinder.special_abilities.SpecialAbility,
        'conditions': pathfinder.conditions.Condition,
        'classes': pathfinder.classes.Class,
        'weapon_enhancements': pathfinder.enhancements.WeaponEnhancement,
        'armor_enhancements': pathfinder.enhancements.ArmorEnhancement
    }

    def pathfinder_data_path(self):
        """
        The path to Pathfinder data files.
        """
        return self.info.path

    def register_pathfinder_data(self):
        """
        Called on PathfinderPlugins so they can register their data.
        """
        reg = pathfinder.data.add_classes
        modname = self.info.machine_name
        for submod, cls in self.data_mapping.iteritems():
            modpath = '%s.%s' % (modname, submod)
            module = mudsling.utils.modules.mod_import(modpath)
            if module is None:
                continue
            exclude = [cls]
            if hasattr(module, '_exclude'):
                exclude.extend(module._exclude)
            reg(cls, module, exclude=exclude)
