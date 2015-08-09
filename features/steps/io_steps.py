from behave import *
from mudsling.testing import *


@when('{name} enter "{text}"')
@when('{name} enters "{text}"')
@when("{name} enter '{text}'")
@when("{name} enters '{text}'")
def enter_text(context, name, text):
    session = get_session(name)
    session.enter_text(text)


@then('{name} should see "{text}"')
@then("{name} should see '{text}'")
def should_see_text(context, name, text, wait=0.1):
    try:
        assert get_session(name).output_contains(text, wait=wait)
    except AssertionError:
        logging.debug(get_session(name).output)
        raise


@then('{name} should see "{text}" in {seconds} seconds')
@then("{name} should see '{text}' in {seconds} seconds")
@then('{name} should see "{text}" in {seconds} second')
@then("{name} should see '{text}' in {seconds} second")
def should_see_text_in_seconds(context, name, text, seconds):
    should_see_text(context, name, text, wait=float(seconds))