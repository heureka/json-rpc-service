import json
import unittest

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



class HandleRequestTest(unittest.TestCase):
    def test_foo(self):
        request = Request(raw_request='{"jsonrpc": "2.0", "id": 321, "method": "foo"}')
        response = service.handle_request(request)

        self.assertEqual(json.loads(response.body()), {"jsonrpc": "2.0", "id": 321, "result": "Foo is not bar."})

    def test_add_with_dict_params(self):
        request = Request(parsed_request={"jsonrpc": "2.0", "id": 321, "method": "add", "params": {"a": 5, "b": 13}})
        response = service.handle_request(request)

        self.assertEqual(json.loads(response.body()), {"jsonrpc": "2.0", "id": 321, "result": 18})

    def test_add_with_list_params(self):
        request = Request(parsed_request={"jsonrpc": "2.0", "id": 321, "method": "add", "params": [5, 13]})
        response = service.handle_request(request)

        self.assertEqual(json.loads(response.body()), {"jsonrpc": "2.0", "id": 321, "result": 18})

    def test_ping(self):
        request = Request(raw_request='{"jsonrpc": "2.0", "id": 321, "method": "ping"}')
        response = service.handle_request(request)

        self.assertEqual(json.loads(response.body()), {"jsonrpc": "2.0", "id": 321, "result": "pong"})

    def test_notification(self):
        request = Request(raw_request='{"jsonrpc": "2.0", "method": "ping"}')
        response = service.handle_request(request)

        self.assertEqual(response.body(), "")

    def test_missing_params(self):
        request = Request(parsed_request={"jsonrpc": "2.0", "id": 321, "method": "add"})
        response = service.handle_request(request)

        self.assertEqual(json.loads(response.body()), {
            "jsonrpc": "2.0",
            "id": 321,
            'error': {
                'code': -32602,
                'message': "add() missing 2 required positional arguments: 'a' and 'b'"
            }
        })

    def test_fail(self):
        request = Request(parsed_request={"jsonrpc": "2.0", "id": 321, "method": "fail"})
        response = service.handle_request(request)

        self.assertEqual(json.loads(response.body()), {
            "jsonrpc": "2.0",
            "id": 321,
            'error': {
                'code': -32603,
                'message': "Internal error."
            }
        })

    def test_fail_as_notification(self):
        request = Request(parsed_request={"jsonrpc": "2.0", "id": 321, "method": "fail"})
        response = service.handle_request(request)

        self.assertEqual(json.loads(response.body()), {
            "jsonrpc": "2.0",
            "id": 321,
            'error': {
                'code': -32603,
                'message': "Internal error."
            }
        })

        self.assertIsInstance(response.exception, NameError)

    def test_fail_with_grace(self):
        request = Request(parsed_request={"jsonrpc": "2.0", "id": 321, "method": "fail_with_grace"})
        response = service.handle_request(request)

        self.assertEqual(json.loads(response.body()), {
            "jsonrpc": "2.0",
            "id": 321,
            'error': {
                'code': -13,
                'message': 'Graceful as a fail whale.',
                'data': 'Graceful!'
            }
        })

        self.assertIsInstance(response.exception, JsonRpcError)
