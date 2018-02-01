import unittest
from jsonrpcservice import Request, ParseError, InvalidRequest


class RequestTest(unittest.TestCase):
    def test_request_without_data(self):
        self.assertRaises(ValueError, Request)

    def test_request_with_raw_input(self):
        request = Request(raw_request='{"jsonrpc": "2.0", "id": 123, "method": "foo"}')

        self.assertEqual(request.parsed_request, {'jsonrpc': '2.0', 'id': 123, 'method': 'foo'})
        self.assertEqual(request.id, 123)
        self.assertEqual(request.method, 'foo')
        self.assertEqual(request.args, [])
        self.assertEqual(request.kwargs, {})

    def test_request_with_parsed_input(self):
        request = Request(parsed_request={'jsonrpc': '2.0', 'id': 123, 'method': 'foo'})

        self.assertEqual(request.parsed_request, {'jsonrpc': '2.0', 'id': 123, 'method': 'foo'})
        self.assertEqual(request.id, 123)
        self.assertEqual(request.method, 'foo')
        self.assertEqual(request.args, [])
        self.assertEqual(request.kwargs, {})

    def test_request_with_array_params(self):
        request = Request(parsed_request={'jsonrpc': '2.0', 'id': 123, 'method': 'foo', 'params': ['abc', 'def']})

        self.assertEqual(request.args, ['abc', 'def'])
        self.assertEqual(request.kwargs, {})

    def test_request_with_object_params(self):
        request = Request(parsed_request={'jsonrpc': '2.0', 'id': 123, 'method': 'foo', 'params': {'abc': 1, 'def': 2}})

        self.assertEqual(request.args, [])
        self.assertEqual(request.kwargs, {'abc': 1, 'def': 2})

    def test_is_notification(self):
        request = Request(parsed_request={'jsonrpc': '2.0', 'id': 123, 'method': 'foo'})
        self.assertFalse(request.is_notification)

        request = Request(parsed_request={'jsonrpc': '2.0', 'method': 'foo'})
        self.assertTrue(request.is_notification)

    def test_parse_error(self):
        request = Request(raw_request="I am little teapot, short and stout.")

        self.assertRaises(ParseError, lambda: request.id)

    def test_invalid_request(self):
        request = Request(parsed_request=[])
        self.assertRaisesRegex(InvalidRequest, 'Expected an object', lambda: request.id)
        self.assertFalse(request.is_notification)

        request = Request(parsed_request={})
        self.assertRaisesRegex(InvalidRequest, 'Missing "jsonrpc"', lambda: request.version)
        self.assertFalse(request.is_notification)

        request = Request(parsed_request={"id": 123})
        self.assertRaisesRegex(InvalidRequest, 'Missing "jsonrpc"', lambda: request.version)
        self.assertEqual(request.id, 123)  # id will be preserved if it can be obtained

        request = Request(parsed_request={"jsonrpc": "2.0"})
        self.assertRaisesRegex(InvalidRequest, 'Missing "method"', lambda: request.method)
        self.assertIs(request.id, None)
        self.assertTrue(request.is_notification)

        request = Request(parsed_request={"jsonrpc": "2.0", "method": 1})
        self.assertRaisesRegex(InvalidRequest, 'must be a string', lambda: request.method)

        request = Request(parsed_request={"jsonrpc": "2.0", "method": "foo"})
        self.assertEqual(request.method, "foo")

        request = Request(parsed_request={"jsonrpc": "2.0", "method": "foo", "params": False})
        self.assertRaisesRegex(InvalidRequest, 'must be either object or array', lambda: request.params)

