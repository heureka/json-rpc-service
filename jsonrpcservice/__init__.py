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

    @property
    @abc.abstractmethod
    def dict(self):
        pass

    @property
    def body(self):
        if self.request.notification:
            return ""
        else:
            return json.dumps(self.dict)


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

    @property
    def dict(self):
        error = {
            'message': self.message,
            'code': self.code,
        }

        if self.data is not None:
            error['data'] = self.data

        try:
            request_id = self.request.id
        except:
            request_id = None

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": error
        }


class SuccessResponse(Response):
    def __init__(self, request, result):
        super().__init__(request)
        self.result = result

    @property
    def dict(self):
        return {
            "jsonrpc": "2.0",
            "id": self.request.id,
            "result": self.result
        }


class Request(object):
    def __init__(self, *, raw_request=None, parsed_request=None):
        if raw_request is None and parsed_request is None:
            raise ValueError('Either "raw_request" or "parsed_request" must be set for Request.')

        self._raw_request = raw_request
        self._parsed_request = parsed_request
        self._dict = None

    @property
    def parsed_request(self):
        if self._parsed_request is None:
            try:
                self._parsed_request = json.loads(self._raw_request)
            except (TypeError, ValueError) as e:
                raise ParseError(message=str(e))

        return self._parsed_request

    @property
    def dict(self):
        if self._dict is None:
            data = self.parsed_request

            if not isinstance(data, dict):
                raise InvalidRequest('Expected an object as request body. Batch requests are not supported.')

            self._dict = data

        return self._dict

    @property
    def id(self):
        return self.dict.get('id')

    @property
    def version(self):
        try:
            return self.dict['jsonrpc']
        except KeyError:
            raise InvalidRequest('Missing "jsonrpc" member in request.')

    @property
    def method(self):
        try:
            method = self.dict['method']
        except KeyError:
            raise InvalidRequest('Missing "method" member in request.')

        if not isinstance(method, str):
            raise InvalidRequest('"method" of request must be a string.')

        return method

    @property
    def params(self):
        if 'params' not in self.dict:
            return None

        if isinstance(self.dict['params'], (list, dict)):
            return self.dict['params']
        else:
            raise InvalidRequest('"params" of request must be either object or array if present.')

    @property
    def args(self):
        if isinstance(self.params, list):
            return self.params
        else:
            return []

    @property
    def kwargs(self):
        if isinstance(self.params, dict):
            return self.params
        else:
            return {}

    @property
    def notification(self):
        # Flag as notification only if client specified protocol correctly and thus should know he can't expect
        # response if id is not set.
        try:
            return self.version == "2.0" and self.id is None
        except InvalidRequest:
            return False


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
        try:
            if request.version != "2.0":
                raise InvalidRequest('Only JSON-RPC version "2.0" is supported.')

            return SuccessResponse(request, self.call_method(request, request.method, request.args, request.kwargs))
        except JsonRpcError as e:
            return ErrorResponse(request, e.code, e.message, e.data)
        except:
            return ErrorResponse(request, -32603, "Internal error.")

    def call_method(self, request, method_name, args, kwargs):
        if method_name not in self._methods:
            raise MethodNotFound('Method "{}" is not defined.'.format(method_name))

        method = self._methods[method_name]

        try:
            inspect.signature(method).bind(*args, **kwargs)
        except TypeError as e:
            raise InvalidParams(str(e))

        return method(*args, **kwargs)
