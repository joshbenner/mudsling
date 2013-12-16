from decimal import Decimal
import functools

import mudsling.storage
import mudsling.pickler


class Currency(object):
    """
    Represents a currency.

    :ivar name: The name of the currency.
    :ivar code: The unique code identifying the currency. This is the value
        that gets pickled, so this code MUST REMAIN THE SAME.
    :ivar exchange_rate: The ratio at which the currency is exchanged.
    """
    __slots__ = ('__name', '__code', '__exchange_rate')

    @property
    def name(self):
        return self.__name

    @property
    def code(self):
        return self.__code

    @property
    def exchange_rate(self):
        return self.__exchange_rate

    def __new__(cls, code, name='', exchange_rate=1.0):
        """
        Enforce singleton currencies, auto-register currency.
        """
        if code in currencies:
            currency = currencies[code]
        else:
            currency = super(Currency, cls).__new__(cls)
            currencies[code] = currency
        return currency

    def __init__(self, code, name='', exchange_rate=1.0):
        """
        :param code: Currency code/abbreviation.
        :type code: str
        :param name: Currency name.
        :type name: str
        :param exchange_rate: The rate at which this currency converts to other
            currencies. This value should be relative to some base currency.
        """
        self.__name = name
        self.__code = code
        self.__exchange_rate = exchange_rate

    def __repr__(self):
        return self.__code

    def set_exchange_rate(self, rate):
        self.__exchange_rate = Decimal(str(rate))

    def format_money(self, amount, show_code=True):
        amount = Decimal(str(amount))
        fmt = "{:,.2f}"
        if show_code:
            fmt += " {}"
        return fmt.format(amount, self.code)

#: The database of registered currencies.
#: :type: dict of Currency
currencies = {}

# [Un]Pickle currency instances using only the code string.
mudsling.pickler.register_external_type(Currency,
                                        lambda c: c.code,
                                        Currency)


@functools.total_ordering
class Money(mudsling.storage.PersistentSlots):
    """
    Represents some amount of money.

    :ivar amount: The amount of money represented.
    :type amount: decimal.Decimal

    :ivar currency: The currency of the money.
    :type currency: Currency
    """
    __slots__ = ('amount', 'currency')

    @property
    def value(self):
        """
        The money's exchange value.
        :rtype: Decimal
        """
        return self.amount * self.currency.exchange_rate

    def __init__(self, amount=0.0, currency='XXX'):
        """
        :type amount: str or int or float or Decimal or Money
        :type currency: str or Currency
        """
        if isinstance(currency, Currency):
            self.currency = currency
        else:
            self.currency = Currency(str(currency))
        if isinstance(amount, Money):
            amount = amount.value / self.currency.exchange_rate
        self.amount = Decimal(str(amount))

    def convert_to(self, currency):
        """
        Obtain a new Money instance of equivalent value in another currency.
        :param currency: The currency to convert to.
        :type currency: str or Currency
        :return: A new Money instance of equivalent value.
        :rtype: Money
        """
        if isinstance(currency, Currency):
            currency = currency
        else:
            currency = Currency(str(currency))
        return Money(self.value / currency.exchange_rate, currency)

    def __repr__(self):
        return self.currency.format_money(self.amount)

    def __pos__(self):
        return Money(self.amount, self.currency)

    def __neg__(self):
        return Money(-self.amount, self.currency)

    def __add__(self, other):
        if isinstance(other, Money):
            return Money(
                (self.value + other.value) / self.currency.exchange_rate,
                self.currency
            )
        else:
            return Money(self.amount + Decimal(str(other)), self.currency)

    __radd__ = __add__

    def __sub__(self, other):
        if isinstance(other, Money):
            return Money(
                (self.value - other.value) / self.currency.exchange_rate,
                self.currency
            )
        else:
            return Money(self.amount - Decimal(str(other)), self.currency)

    def __rsub__(self, other):
        # Not called if other is Money.
        return Money(Decimal(str(other)) - self.amount, self.currency)

    def __mul__(self, other):
        if isinstance(other, Money):
            raise TypeError("Cannot multiply monies by eachother")
        else:
            return Money(self.amount * Decimal(str(other)), self.currency)

    __rmul__ = __mul__

    def __div__(self, other):
        if isinstance(other, Money):
            raise TypeError("Cannot divide monies by eachother")
        else:
            return Money(self.amount / Decimal(str(other)), self.currency)

    def __rdiv__(self, other):
        # Not called if other is Money.
        return Money(Decimal(str(other)) / self.amount, self.currency)

    def __eq__(self, other):
        if isinstance(other, Money):
            return self.value == other.value
        return self.amount == Decimal(str(other))

    def __lt__(self, other):
        if isinstance(other, Money):
            return self.value < other.value
        return self.amount < Decimal(str(other))
