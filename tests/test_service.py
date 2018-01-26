import json
import unittest
from jsonrpcservice import Service, Request, JsonRpcError, ErrorResponse, SuccessResponse
from . import foo_module


class AddingMethodsTest(unittest.TestCase):
    def test_add_method(self):
        service = Service()

        def foo():
            pass

        service.add_method("foolific", foo)

        self.assertEqual(service.get_methods(), {"foolific": foo})

        self.assertRaises(ValueError, service.add_method, "foolific", foo)

    def test_decorator(self):
        service = Service()

        @service.method
        def foo():
            pass

        @service.method
        def bar():
            pass

        self.assertEqual(service.get_methods(), {"foo": foo, "bar": bar})

    def test_add_methods_for_module(self):
        service = Service()
        service.add_methods(foo_module, "foo.")

        self.assertEqual(service.get_methods(), {"foo.foo": foo_module.foo, "foo.bar": foo_module.bar})

    def test_add_methods_as_dict(self):
        service = Service()
        service.add_methods({"foo": foo_module.foo, "bar": foo_module.bar})

        self.assertEqual(service.get_methods(), {"foo": foo_module.foo, "bar": foo_module.bar})

    def test_add_methods_as_list(self):
        service = Service()
        service.add_methods([foo_module.foo, foo_module.bar])

        self.assertEqual(service.get_methods(), {"foo": foo_module.foo, "bar": foo_module.bar})
