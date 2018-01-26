import abc
import inspect
import json

import sys


class JsonRpcError(Exception):
    def __init__(self, code, message, data=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class ParseError(JsonRpcError):
    code = -32700

    def __init__(self, message="Parse error", data=None):
        super().__init__(self.code, message, data)


class InvalidRequest(JsonRpcError):
    code = -32600

    def __init__(self, message="Invalid request", data=None):
        super().__init__(self.code, message, data)


class MethodNotFound(JsonRpcError):
    code = -32601

    def __init__(self, message="Method not found", data=None):
        super().__init__(self.code, message, data)


class InvalidParams(JsonRpcError):
    code = -32602

    def __init__(self, message="Invalid params", data=None):
        super().__init__(self.code, message, data)


class InternalError(JsonRpcError):
    code = -32603

    def __init__(self, message="Internal error", data=None):
        super().__init__(self.code, message, data)


class ApplicationError(JsonRpcError):
    def __init__(self, code, message="Application error", data=None):
        if -32000 >= code >= -32768:
            raise ValueError("Error codes between -32000 and -32768 are reserved by JSON-RPC 2.0 specification.")

        super().__init__(code, message, data)


class Response(object, metaclass=abc.ABCMeta):
    def __init__(self, request):
        self.request = request

    @abc.abstractmethod
    def dict(self):
        pass

    def body(self):
        if self.request.is_notification():
            return ""
        else:
            return json.dumps(self.dict())


class ErrorResponse(Response):
    def __init__(self, request, code, message, data=None, exc_info=True):
        super().__init__(request)
        self.code = code
        self.message = message
        self.data = data

        if exc_info is True:
            self.exc_info = sys.exc_info()
        else:
            self.exc_info = exc_info


    def dict(self):
        error = {
            'message': self.message,
            'code': self.code,
        }

        if self.data is not None:
            error['data'] = self.data

        return {
            "jsonrpc": "2.0",
            "id": self.request.id(),
            "error": error
        }


class SuccessResponse(Response):
    def __init__(self, request, result):
        super().__init__(request)
        self.result = result

    def dict(self):
        return {
            "jsonrpc": "2.0",
            "id": self.request.id(),
            "result": self.result
        }


class Request(object):
    def __init__(self, raw_request=None, parsed_request=None):
        self._id = None
        self._method = None
        self._args = []
        self._kwargs = {}
        self._notification = False
        self._prepared = False

        if raw_request is None and parsed_request is None:
            raise ValueError('Either "raw_request" or "parsed_request" must be set for Request.')

        self._raw_request = raw_request
        self._parsed_request = parsed_request

    def parsed_request(self):
        if self._parsed_request is None:
            try:
                self._parsed_request = json.loads(self._raw_request)
            except (TypeError, ValueError) as e:
                raise ParseError(message=str(e))

        return self._parsed_request

    def id(self):
        self._prepare()
        return self._id

    def method(self):
        self._prepare()
        return self._method

    def args(self):
        self._prepare()
        return self._args

    def kwargs(self):
        self._prepare()
        return self._kwargs

    def is_notification(self):
        self._prepare()
        return self._notification

    def _prepare(self):
        if self._prepared:
            return

        self._prepared = True

        data = self.parsed_request()

        if not isinstance(data, dict):
            raise InvalidRequest('Expected an object as request body. Batch requests are not supported.')

        # Remember `id` as the first thing. `id` can be ommited for notifications.
        self._id = data.get('id')

        if 'jsonrpc' not in data:
            raise InvalidRequest('Missing "jsonrpc" member in request.')

        if data['jsonrpc'] != "2.0":
            raise InvalidRequest('Only JSON-RPC version "2.0" is supported.')

        if self._id is None:
            # Flag as notification only if client specified protocol correctly and thus should know he can't expect
            # response if id is not set.
            self._notification = True

        if 'method' not in data:
            raise InvalidRequest('Missing "method" member in request.')

        if not isinstance(data['method'], str):
            raise InvalidRequest('"method" of request must be a string.')

        self._method = data['method']

        if 'params' in data:
            if isinstance(data['params'], list):
                self._args.extend(data['params'])
            elif isinstance(data['params'], dict):
                self._kwargs.update(data['params'])
            else:
                raise InvalidRequest('"params" of request must be either object or array if present.')


class Service(object):
    def __init__(self):
        self._methods = {}

    def method(self, method):
        if callable(method):
            self.add_method(method.__name__, method)

            return method
        else:
            def wrapper(func):
                self.add_method(method, func)
                return func

            return wrapper

    def add_method(self, method_name, func):
        if method_name in self._methods:
            raise ValueError('Method "{}" already registered.'.format(method_name))

        self._methods[method_name] = func

    def add_methods(self, methods, prefix=''):
        if isinstance(methods, (list, tuple)):
            methods = {method.__name__: method for method in methods}
        elif not isinstance(methods, dict):
            methods = {method: getattr(methods, method) for method in dir(methods) if not method.startswith('_')}

        for name, method in methods.items():
            if callable(method):
                self.add_method(prefix + name, method)

    def get_methods(self):
        return self._methods.copy()

    def handle_request(self, request):
        response = None
        try:
            method_name, args, kwargs = self.before_call(request, request.method(), request.args(), request.kwargs())
            response = SuccessResponse(request, self.call_method(request, method_name, args, kwargs))
        except JsonRpcError as e:
            response = ErrorResponse(request, e.code, e.message, e.data)
        except:
            response = ErrorResponse(request, -32603, "Internal error.")
        finally:
            return self.after_call(request, response)

    def before_call(self, request, method_name, args, kwargs):
        return method_name, args, kwargs

    def after_call(self, request, response):
        return response

    def call_method(self, request, method_name, args, kwargs):
        if method_name not in self._methods:
            raise MethodNotFound('Method "{}" is not defined.'.format(method_name))

        method = self._methods[method_name]

        try:
            inspect.getcallargs(method, *request.args(), **request.kwargs())
        except TypeError as e:
            raise InvalidParams(str(e))

        return method(*request.args(), **request.kwargs())
