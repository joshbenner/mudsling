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

    def and_(self, other):
        """
        :param other: The other Specification to consider in addition.
        :type other: Specification

        :return: AndSpecification
        """
        return AndSpecification(self, other)

    def or_(self, other):
        """
        :param other: The other specification to consider alternately.
        :type other: Specification

        :return: OrSpecification
        """
        return OrSpecification(self, other)

    def not_(self):
        """
        Invert this specification.

        :return: NotSpecification
        """
        return NotSpecification(self)


class AndSpecification(Specification):
    """
    Satisfied only if both left and right are satisfied.
    """

    def __init__(self, left, right):
        """
        :param left: The left specification.
        :type left: Specification
        :param right: The right specification.
        :type right: Specification
        """
        self.left = left
        self.right = right

    def satisfied_by(self, candidate):
        """:rtype: bool"""
        return (self.left.satisfied_by(candidate)
                and self.right.satisfied_by(candidate))


class OrSpecification(Specification):
    """
    Satisfied only if either left or right are satisfied.
    """

    def __init__(self, left, right):
        """
        :param left: The left specification.
        :type left: Specification
        :param right: The right specification.
        :type right: Specification
        """
        self.left = left
        self.right = right

    def satisfied_by(self, candidate):
        """:rtype: bool"""
        return (self.left.satisfied_by(candidate)
                or self.right.satisfied_by(candidate))


class NotSpecification(Specification):
    """
    A specification that is satisfied if none of its nested specifications are
    satisfied.
    """

    def __init__(self, spec):
        """
        :param spec: The spec that must not be satisfied.
        :type spec: Specification
        """
        self.spec = spec

    def satisfied_by(self, candidate):
        """:rtype: bool"""
        return not self.spec.satisfied_by(candidate)
