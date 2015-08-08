from behave import *
from mudsling.testing import *


@when('{name} enter "{text}"')
@when('{name} enters "{text}"')
@when("{name} enter '{text}'")
@when("{name} enters '{text}'")
def enter_text(context, name, text):
    session = get_session(name)
    session.receive_input(text)


@then('{name} should see "{text}"')
@then("{name} should see '{text}'")
def should_see_text(context, name, text):
    assert get_session(name).output_contains(text)