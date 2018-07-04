import json
import unittest
from functools import wraps

from jsonrpcservice import Service, JsonRpcError, Request

service = Service()
service.add_method("ping", lambda: "pong")


@service.method('foo')
def what_is_foo():
    return "Foo is not bar."


@service.method
def add(a, b):
    return a + b


@service.method
def fail():
    return i_dont_know_what_i_am_doing()


@service.method
def fail_with_grace():
    raise JsonRpcError(-13, "Graceful as a fail whale.", "Graceful!")


def inject_arg_decorator(func):
    @wraps(func)
    def wrapper(a):
        return func(a, 10)

    return wrapper


@service.method
@inject_arg_decorator
def injected_arg(a, b):
    """`a` is required, `b` is injected by decorator."""
    return a + b


class HandleRequestTest(unittest.TestCase):
    def test_foo(self):
        request = Request(raw_request='{"jsonrpc": "2.0", "id": 321, "method": "foo"}')
        response = service.handle_request(request)

        self.assertEqual(json.loads(response.body), {"jsonrpc": "2.0", "id": 321, "result": "Foo is not bar."})

    def test_add_with_dict_params(self):
        request = Request(parsed_request={"jsonrpc": "2.0", "id": 321, "method": "add", "params": {"a": 5, "b": 13}})
        response = service.handle_request(request)

        self.assertEqual(json.loads(response.body), {"jsonrpc": "2.0", "id": 321, "result": 18})

    def test_add_with_list_params(self):
        request = Request(parsed_request={"jsonrpc": "2.0", "id": 321, "method": "add", "params": [5, 13]})
        response = service.handle_request(request)

        self.assertEqual(json.loads(response.body), {"jsonrpc": "2.0", "id": 321, "result": 18})

    def test_ping(self):
        request = Request(raw_request='{"jsonrpc": "2.0", "id": 321, "method": "ping"}')
        response = service.handle_request(request)

        self.assertEqual(json.loads(response.body), {"jsonrpc": "2.0", "id": 321, "result": "pong"})

    def test_notification(self):
        request = Request(raw_request='{"jsonrpc": "2.0", "method": "ping"}')
        response = service.handle_request(request)

        self.assertEqual(response.body, "")

    def test_missing_params(self):
        request = Request(parsed_request={"jsonrpc": "2.0", "id": 321, "method": "add"})
        response = service.handle_request(request)

        self.assertEqual(json.loads(response.body), {
            "jsonrpc": "2.0",
            "id": 321,
            'error': {
                'code': -32602,
                'message': "missing a required argument: 'a'"
            }
        })

    def test_fail(self):
        request = Request(parsed_request={"jsonrpc": "2.0", "id": 321, "method": "fail"})
        response = service.handle_request(request)

        self.assertEqual(json.loads(response.body), {
            "jsonrpc": "2.0",
            "id": 321,
            'error': {
                'code': -32603,
                'message': "Internal error"
            }
        })

    def test_fail_as_notification(self):
        request = Request(parsed_request={"jsonrpc": "2.0", "method": "fail"})
        response = service.handle_request(request)

        self.assertEqual(response.body, "")

        self.assertIsInstance(response.exc_info[1], NameError)

    def test_fail_with_grace(self):
        request = Request(parsed_request={"jsonrpc": "2.0", "id": 321, "method": "fail_with_grace"})
        response = service.handle_request(request)

        self.assertEqual(json.loads(response.body), {
            "jsonrpc": "2.0",
            "id": 321,
            'error': {
                'code': -13,
                'message': 'Graceful as a fail whale.',
                'data': 'Graceful!'
            }
        })

        self.assertIsInstance(response.exc_info[1], JsonRpcError)

    def test_injected_arg(self):
        """Test that only one argument is required (method signature is detected correctly)."""

        request = Request(parsed_request={"jsonrpc": "2.0", "id": 321, "method": "injected_arg", "params": []})
        response = service.handle_request(request)

        self.assertEqual(json.loads(response.body), {
            "jsonrpc": "2.0",
            "id": 321,
            "error": {
                "code": -32602,
                "message": "missing a required argument: 'a'"
            }
        })

        request = Request(parsed_request={"jsonrpc": "2.0", "id": 321, "method": "injected_arg", "params": [1]})
        response = service.handle_request(request)

        self.assertEqual(json.loads(response.body), {
            "jsonrpc": "2.0",
            "id": 321,
            "result": 11
        })

    def test_parse_error(self):
        request = Request(raw_request="foo")
        response = service.handle_request(request)

        self.assertEqual(json.loads(response.body), {
            'id': None,
            'jsonrpc': '2.0',
            'error': {
                'code': -32700,
                'message': 'Expecting value: line 1 column 1 (char 0)'
            }
        })
