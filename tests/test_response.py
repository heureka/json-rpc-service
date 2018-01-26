import json
import unittest

from jsonrpcservice import Request, SuccessResponse, ErrorResponse


class ResponseTest(unittest.TestCase):
    def test_success_response(self):
        result = {"foo": "bar"}

        request = Request(parsed_request={"jsonrpc": "2.0", "id": 123, "method": "foo"})
        response = SuccessResponse(request, result)

        self.assertEqual(response.dict(), {"jsonrpc": "2.0", "id": 123, "result": result})
        self.assertEqual(json.loads(response.body()), {"jsonrpc": "2.0", "id": 123, "result": result})

    def test_success_response_for_notification(self):
        result = {"foo": "bar"}

        request = Request(parsed_request={"jsonrpc": "2.0", "method": "foo"})
        response = SuccessResponse(request, result)

        self.assertEqual(response.dict(), {"jsonrpc": "2.0", "id": None, "result": result})
        self.assertEqual(response.body(), "")

    def test_error_response(self):
        request = Request(parsed_request={"jsonrpc": "2.0", "id": 123, "method": "foo"})
        response = ErrorResponse(request, -123, "Out of icecream.", exception="Just so you know.")

        expected = {
            "jsonrpc": "2.0",
            "id": 123,
            "error": {
                "message": "Out of icecream.",
                "code": -123
            }
        }

        self.assertEqual(response.dict(), expected)
        self.assertEqual(json.loads(response.body()), expected)
        self.assertEqual(response.exception, "Just so you know.")

    def test_error_response_for_notification(self):
        request = Request(parsed_request={"jsonrpc": "2.0", "method": "foo"})
        response = ErrorResponse(request, -123, "Out of icecream.", data={"mood": "sad"})

        expected = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "message": "Out of icecream.",
                "code": -123,
                "data": {
                    "mood": "sad"
                }
            }
        }

        self.assertEqual(response.dict(), expected)
        self.assertEqual(response.body(), "")
        self.assertIsNone(response.exception)

