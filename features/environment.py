from shutil import rmtree

from behave.runner import ContextMaskWarning

from mudsling.testing import bootstrap_game, TestSession


def add_game_to_context(context, data_path=None, params=(), settings_text=''):
    """
    Attach a bootstrapped test game to the context.

    :param context: The context to attach the game to.
    :type context: behave.runner.Context
    """
    if 'game' not in context:
        context.game = bootstrap_game(data_path, params, settings_text)


def remove_game_from_context(context):
    """
    Remove the test game instance if possible.

    :type context: behave.runner.Context
    """
    if 'game' in context:
        game = context.game
        try:
            del context.game
        except ContextMaskWarning:
            pass  # We tried!
        else:
            rmtree(game.game_dir)


def open_session(context):
    if 'session' not in context:
        context.session = TestSession(context.game)
    return context.session


def close_session(context):
    if 'session' in context:
        try:
            context.session.disconnect(reason='test session over')
        except ContextMaskWarning:
            pass


def before_scenario(context, scenario):
    """
    Bootstrap the game for each scenario, unless it has already been
    bootstrapped at a higher level.

    :type context: behave.runner.Context
    :type scenario: behave.model.Scenario
    """
    add_game_to_context(context)
    open_session(context)


def after_scenario(context, scenario):
    """
    Remove the test game instance if it was added in this scenario.

    :type context: behave.runner.Context
    :type scenario: behave.model.Scenario
    """
    close_session(context)
    remove_game_from_context(context)


def after_feature(context, feature):
    """
    Remove the test game instance if it was added at the feature level.

    :type context: behave.runner.Context
    :type feature: behave.model.Feature
    """
    close_session(context)
    remove_game_from_context(context)