"""
Player/account-related API-level operations.
"""
from mudsling import registry

from mudsling import utils
import mudsling.utils.string


def createPlayer(names, email, password=None):
    password = password or utils.string.randomString(10)

