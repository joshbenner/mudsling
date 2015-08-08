

def get_game(context):
    """:rtype: mudsling.core.MUDSling"""
    return context.game


def get_session(context):
    """:rtype: mudsling.testing.TestSession"""
    return context.session