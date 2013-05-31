import logging

from mudsling.utils.sequence import CaselessDict


class ClassRegistry(object):
    """
    The class registry keeps a mapping of python classes and their 'pretty'
    names as shown in-game. The registry is built at runtime.
    """

    #: @type: L{mudsling.utils.sequence.CaselessDict}
    classes = None

    def __init__(self):
        self.classes = CaselessDict()

    def build_class_registry(self, game):
        """
        Builds a class registry for all classes which can be @create'd in-game.
        We do this so that we can have friendly names and easily produce lists
        of object types.

        The MUDSling server doesn't register its base classes; however, some
        classes are registered by the MUDSlingCore default plugin.

        Invokes hook object_classes and expects responding plugins to return a
        list of (name, class) tuples.
        """
        classes = game.invoke_hook('object_classes')
        for plugin, response in classes.iteritems():
            if not isinstance(response, list):
                continue
            try:
                for name, cls in response:
                    if name in self.classes:
                        logging.info("Duplicate class name: %s" % name)
                        replaced = self.classes[name]
                        alt = replaced.__module__ + '.' + replaced.__name__
                        self.classes[alt] = replaced
                    self.classes[name] = cls
            except TypeError:
                err = "Invalid class registration from %s" % plugin.name
                logging.error(err)

    def get_class(self, name):
        """
        Searches the class registry for a class matching the given name.
        @param name: The class name to search for.
        @return: The class with the specified pretty name.
        """
        if name in self.classes:
            return self.classes[name]
        return None

    def get_class_name(self, cls):
        """
        Given a class, find the class registry name that corresponds to it.
        @param cls: The class whose pretty name to retrieve.
        @return: The pretty name of the class.
        @rtype: str or None
        """
        for name, obj in self.classes.iteritems():
            if obj == cls:
                return name
        return None


class PlayerRegistry(object):
    """
    Player registry expects one player per name, but multiple players per
    email address.
    """
    def __init__(self):
        self.players = []
        self.names = {}
        self.emails = {}

    def find_by_name(self, name):
        if name in self.names:
            return self.names[name]
        return None

    def find_by_email(self, email):
        """
        @rtype: C{list}
        """
        if email in self.emails:
            return self.emails[email]
        return []

    def register_player(self, player):
        """
        Adds a player to the registry.

        @param player: The player object to register.
        @type player: L{mudsling.objects.BasePlayer}
        """
        #: @type: mudsling.objects.BasePlayer
        player = player._real_object()
        if player in self.players:
            self.unregister_player(player)
        self.players.append(player)
        for name in player.names:
            self.names[name] = player
        if player.email not in self.emails:
            self.emails[player.email] = []
        self.emails[player.email].append(player)

    def register_players(self, players):
        for player in players:
            self.register_player(player)

    def unregister_player(self, player):
        """
        @type player: L{mudsling.objects.BasePlayer}
        """
        names_to_delete = []
        #: @type: mudsling.objects.BasePlayer
        player = player._real_object()
        if player in self.players:
            self.players.remove(player)
        for name, p in self.names.iteritems():
            if p == player:
                names_to_delete.append(name)
        for name in names_to_delete:
            del self.names[name]

        for email, players in self.emails.iteritems():
            if p in players:
                self.emails[email].remove(p)

    def reregister_player(self, player):
        self.unregister_player(player)
        self.register_player(player)


# Canonical registry instances.
classes = ClassRegistry()
players = PlayerRegistry()
