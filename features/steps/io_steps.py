from behave import *

from utils import *


@when('I enter "{text}"')
def enter_text(context, text):
    session = get_session(context)
    session.receive_input(text)


@then('I should see "{text}"')
def should_see_text(context, text):
    text = str(text)
    assert context.session.output_contains(text)