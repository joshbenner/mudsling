from behave import *

from mudsling.testing import *
from mudsling.parsers import ObjClassStaticParser


@given('A {objclass} called "{name}" exists')
@given('An {objclass} called "{name}" exists')
@given('A {objclass} object called "{name}" exists')
@given('An {objclass} object called "{name}" exists')
@given('A {objclass} exists called "{name}"')
@given('An {objclass} exists called "{name}"')
@given('A {objclass} object exists called "{name}"')
@given('An {objclass} object exists called "{name}"')
def object_exists(context, objclass, name):
    cls = ObjClassStaticParser.parse(objclass)
    obj = cls.create(names=(name,))
    add_cleanup(CleanupObj(obj))
    context.objects[name] = obj
    logging.info('Created %s called "%s"'
                 % (ObjClassStaticParser.unparse(cls), name))


@given('{obj} is in {location}')
def object_in_location(context, obj, location):
    obj = context.objects[obj]
    location = context.objects[location]
    obj.move_to(location)