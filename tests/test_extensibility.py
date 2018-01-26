import json
import unittest

from jsonrpcservice import Service, SuccessResponse, Request, JsonRpcError


class CustomException(Exception):
    pass


class CustomService(Service):
    def __init__(self, language):
        super().__init__()
        self.default_language = language

    def before_call(self, request, method_name, args, kwargs):
        if 'language' not in kwargs:
            kwargs['language'] = self.default_language

        request.started_at = 123000

        return method_name, args, kwargs

    def after_call(self, request, response):
        if isinstance(response, SuccessResponse):
            response.result['_timing'] = 124000 - request.started_at

        return response

    def call_method(self, *args, **kwargs):
        try:
            return super().call_method(*args, **kwargs)
        except CustomException as e:
            raise JsonRpcError(-2288, "There is some custom problem.", data=str(e))


service = CustomService('en')


@service.method
def get_donut(language):
    if language == 'en':
        return {"message": "Here, have this donut."}
    elif language == 'cs':
        return {"message": "Na, tu máš koblihu."}
    else:
        raise CustomException('Unknown language "{}".'.format(language))


class TestExtensibility(unittest.TestCase):
    def test_default_language(self):
        request = Request(raw_request='{"jsonrpc": "2.0", "id": 666, "method": "get_donut"}')
        response = service.handle_request(request)

        self.assertEqual(json.loads(response.body()), {
            "jsonrpc": "2.0",
            "id": 666,
            "result": {
                "message": "Here, have this donut.",
                "_timing": 1000
            }
        })

    def test_language_in_params(self):
        request = Request(
            raw_request='{"jsonrpc": "2.0", "id": 666, "method": "get_donut", "params": {"language": "cs"}}'
        )
        response = service.handle_request(request)

        self.assertEqual(json.loads(response.body()), {
            "jsonrpc": "2.0",
            "id": 666,
            "result": {
                "message": "Na, tu máš koblihu.",
                "_timing": 1000
            }
        })

    def test_custom_error_handling(self):
        request = Request(
            raw_request='{"jsonrpc": "2.0", "id": 666, "method": "get_donut", "params": {"language": "lg"}}'
        )
        response = service.handle_request(request)

        self.assertEqual(json.loads(response.body()), {
            "jsonrpc": "2.0",
            "id": 666,
            'error': {
                'code': -2288,
                'data': 'Unknown language "lg".',
                'message': 'There is some custom problem.'
            }
        })
