from mudsling.storage import PersistentSlots
from mudsling.objects import Object


class Sensation(PersistentSlots):
    """Generic sensation superclass.

    Traits are essentially tags that describe the sensation. Examples:
    * loud
    * bright
    * bitter
    * soft
    """
    __slots__ = ('content', 'origin', 'traits')

    sensed_by = set()
    """Which senses can detect this sensation?"""

    def __init__(self, content, origin=None, traits=set()):
        self.content = content
        self.origin = origin
        self.traits = set(traits)


class Sound(Sensation):
    """A sension which can be heard."""
    sensed_by = {'hearing'}


class Speech(Sound):
    """A specific type of sound produced by audible language."""
    pass


class Sight(Sensation):
    """A sensation which can be seen."""
    sensed_by = {'vision'}


class SensoryMedium(Object):
    """A medium through which :class:`Sensation` instances may propagate.

    :ivar senses: The senses this medium can propagate.
    :type senses: set
    """

    senses = set()

    def propagate_sensation(self, sensation, exclude=None):
        """Propagates a sensation through the medium to its contents.

        :param sensation: The sensation to propagate.
        :type sensation: Sensation

        :returns: A list of objects that sensed the sensation.
        :rtype: list
        """
        sensed_by = []
        exclude = exclude or []
        senses = self.senses.intersection(sensation.sensed_by)
        for obj in (o for o in self._contents if o not in exclude):
            if obj.isa(SensingObject) and obj.has_any_sense(senses):
                obj.sense(sensation)
                sensed_by.append(obj)
        return sensed_by


class SensingObject(Object):
    """An object that has senses.

    To implement a sense, the object must provide methods which map to the
    senses to be available to the object.

    Example:
    >>> class Camera(SensingObject):
    >>>     def __init__(self):
    >>>         self.images = []
    >>>         super(SensingObject, self).__init__()
    >>>
    >>>     def vision_sense(self, sight):
    >>>         self.images.append(sight.content)
    """

    def _sense_function_name(self, sense):
        """Returns the name of the function called when sensing a sensation of
        the indicated type.

        :param sense: The sense the function is related to.
        :rtype: str
        """
        return "%s_sense" % sense

    def has_sense(self, sense):
        """Whether this object has the named sense.

        :param sense: The sense to inquire about.
        :type sense: str

        :rtype: bool
        """
        m = getattr(self, self._sense_function_name(sense), None)
        return callable(m)

    def has_any_sense(self, senses):
        """Whether this object has any of the indicated senses.

        :param senses: The senses to inquire about.
        :type senses: list or tuple or set or dict
        :rtype: bool
        """
        for sense in senses:
            if self.has_sense(sense):
                return True
        return False

    def can_sense(self, sensation):
        """Whether or not this can sense a given sensation.
        :param sensation: The sensation in question.
        :type sensation: Sensation
        :rtype: bool
        """
        return self.has_any_sense(sensation.sensed_by)

    @property
    def can_see(self):
        return self.has_sense('vision')

    @property
    def can_hear(self):
        return self.has_sense('hearing')

    def sense(self, sensation):
        """Senses a sensation.

        :param sensation: The sensation to sense.
        :type sensation: Sensation
        """
        for sense in sensation.sensed_by:
            func_name = self._sense_function_name(sense)
            try:
                func = getattr(self, func_name)
            except AttributeError:
                continue
            func(sensation)

    def emit(self, msg, exclude=None, location=None):
        """
        Version of emit which accepts sensations. If the input is a simple
        string, then the emit is assumed to be a :class:`Sight`.

        :param msg: Text or sensation to emit.
        :type msg: str or list or dict or Sensation
        :param exclude: List of objects to NOT notify of the emit.
        :type exclude: list or set or tuple or None
        :param location: Where the emission takes place.
        :type location: Object or SensoryMedium

        :return: The list of objects which were subject to the emission.
        :rtype: list
        """
        if location is None:
            location = self.location
        if isinstance(msg, basestring):
            msg = Sight(msg)
        if isinstance(msg, Sensation):
            if location is not None and location.isa(SensoryMedium):
                return location.propagate_sensation(msg, exclude=exclude)
        else:
            return super(SensingObject, self).emit(msg, exclude, location)
