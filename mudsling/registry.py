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

    def buildClassRegistry(self, game):
        """
        Builds a class registry for all classes which can be @create'd in-game.
        We do this so that we can have friendly names and easily produce lists
        of object types.

        The MUDSling server doesn't register its base classes; however, some
        classes are registered by the MUDSlingCore default plugin.

        Invokes hook_objectClasses and expects responding plugins to return a
        list of (name, class) tuples.
        """
        classes = game.invokeHook('objectClasses')
        for plugin, response in classes.iteritems():
            if not isinstance(response, list):
                continue
            try:
                for name, cls in response:
                    if name in self.classes:
                        logging.error("Duplicate class name: %s" % name)
                        alt = cls.__module__ + '.' + cls.__name__
                        self.classes[alt] = cls
                    else:
                        self.classes[name] = cls
            except TypeError:
                err = "Invalid class registration from %s" % plugin.name
                logging.error(err)

    def getClass(self, name):
        """
        Searches the class registry for a class matching the given name.
        @param name: The class name to search for.
        @return: The class with the specified pretty name.
        """
        if name in self.classes:
            return self.classes[name]
        return None

    def getClassName(self, cls):
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
        self.names = {}
        self.emails = {}

    def findByName(self, name):
        if name in self.names:
            return self.names[name]
        return None

    def findByEmail(self, email):
        """
        @rtype: C{list}
        """
        if email in self.emails:
            return self.emails[email]
        return []

    def registerPlayer(self, player):
        """
        Adds a player to the registry.

        @param player: The player object to register.
        @type player: L{mudsling.objects.BasePlayer}
        """
        #: @type: mudsling.objects.BasePlayer
        player = player._realObject()
        for name in player.names:
            self.names[name] = player
        if player.email not in self.emails:
            self.emails[player.email] = []
        self.emails[player.email].append(player)

    def registerPlayers(self, players):
        for player in players:
            self.registerPlayer(player)

    def unregisterPlayer(self, player):
        """
        @type player: L{mudsling.objects.BasePlayer}
        """
        names_to_delete = []
        #: @type: mudsling.objects.BasePlayer
        player = player._realObject()
        for name, p in self.names.iteritems():
            if p == player:
                names_to_delete.append(name)
        for name in names_to_delete:
            del self.names[name]

        emails_to_delete = []
        for email, p in self.emails.iteritems():
            if p == player:
                emails_to_delete.append(email)
        for email in emails_to_delete:
            del self.emails[email]

    def reregisterPlayer(self, player):
        self.unregisterPlayer(player)
        self.registerPlayer(player)


# Canonical registry instances.
classes = ClassRegistry()
players = PlayerRegistry()
