"""Module used for test of method adding."""
from tests.bar_module import dangerous_thing

some_var = "Nope"
dangerous_var = dangerous_thing
callable_but_not_defined = lambda: True


def foo():
    pass


def bar():
    pass


def _something_dangerous():
    pass


foo_alias = foo