from behave import given, when, then, step


@given('The player "{name}" exists')
def player_exists(context, name):
    raise NotImplementedError()