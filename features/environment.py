from shutil import rmtree

from behave.runner import ContextMaskWarning

from mudsling.testing import *


def before_all(context):
    context.game = bootstrap_game()


def after_all(context):
    if 'game' in context:
        game = context.game
        try:
            del context.game
        except ContextMaskWarning:
            pass  # We tried!
        else:
            rmtree(game.game_dir)


def before_scenario(context, scenario):
    """
    Bootstrap the game for each scenario, unless it has already been
    bootstrapped at a higher level.

    :type context: behave.runner.Context
    :type scenario: behave.model.Scenario
    """
    context.cleanup = []
    context.session = TestSession(context.game)


def after_scenario(context, scenario):
    """
    Remove the test game instance if it was added in this scenario.

    :type context: behave.runner.Context
    :type scenario: behave.model.Scenario
    """
    context.session.disconnect(reason='Scenario over')
    cleanup(context.cleanup)
