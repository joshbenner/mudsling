from abc import ABCMeta, abstractmethod


class Specification(object):
    """
    Abstract specification object that can form a tree of conditions.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def satisfied_by(self, candidate):
        """
        Indicates whether a candidate object satisfies this specification.

        :param candidate: The candidate object to consider.
        :type candidate: object

        :returns: True if candidate satisfies specification, else False.
        :rtype: bool
        """
        pass

    def And(self, other):
        """
        :param other: The other Specification to consider in addition.
        :type other: Specification

        :return: AndSpecification
        """
        return AndSpecification(self, other)


class CompositeSpecification(Specification):
    """
    An abstract specification whose satisfaction is composed of the satisfaction
    of nested specifications.
    """
    def __init__(self, *specifications):
        """
        :param specifications: The specifications which compose this spec.
        :type specifications: list of Specification
        """
        self.specifications = specifications

    def _composite_satisfaction(self, candidate):
        """
        :returns: Generator for the satisfaction of the nested specifications.
        :rtype: __generator of bool
        """
        return (spec.satisfied_by(candidate) for spec in self.specifications)


class AndSpecification(CompositeSpecification):
    """
    A specification that is satisfied if all its nested specifications are
    satisfied.
    """
    def satisfied_by(self, candidate):
        """:rtype: bool"""
        return all(self._composite_satisfaction(candidate))


class OrSpecification(CompositeSpecification):
    """
    A specification that is satisfied if any of its nested specifications are
    satisfied.
    """
    def satisfied_by(self, candidate):
        """:rtype: bool"""
        return any(self._composite_satisfaction(candidate))


class NotSpecification(CompositeSpecification):
    """
    A specification that is satisfied if none of its nested specifications are
    satisfied.
    """
    def satisfied_by(self, candidate):
        """:rtype: bool"""
        return not any(self._composite_satisfaction(candidate))
