from shutil import rmtree

from mudsling.testing import *


def before_all(context):
    context.game = bootstrap_game()
    context.objects = {}


def after_all(context):
    if game is not None:
        rmtree(game().game_dir)


def before_feature(context, feature):
    set_cleanup_context(feature)


def after_feature(context, feature):
    cleanup(feature)


def before_scenario(context, scenario):
    """
    Bootstrap the game for each scenario, unless it has already been
    bootstrapped at a higher level.

    :type context: behave.runner.Context
    :type scenario: behave.model.Scenario
    """
    set_cleanup_context(scenario)


def after_scenario(context, scenario):
    """
    Remove the test game instance if it was added in this scenario.

    :type context: behave.runner.Context
    :type scenario: behave.model.Scenario
    """
    cleanup(scenario)
