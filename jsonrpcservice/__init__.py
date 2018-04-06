import abc
import inspect
import json

import sys


class JsonRpcError(Exception):
    """Base for JSON-RPC errors.

    Such errors can be translated into error response, other errors will be reported as internal error by
    JSON-RPC service.

    Attributes:
        code (int): Error code
        message (str): Error message
        data (Any): Arbitrary user data about the error.
    """
    def __init__(self, code, message, data=None):
        """
        Args:
            code (int): Error code
            message (str): Error message
            data (Any): Arbitrary user data about the error.
        """
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class ParseError(JsonRpcError):
    """Error raised when request is not a valid JSON."""
    code = -32700

    def __init__(self, message="Parse error", data=None):
        super().__init__(self.code, message, data)


class InvalidRequest(JsonRpcError):
    """Error raised when request is not a valid JSON-RPC 2.0 request."""
    code = -32600

    def __init__(self, message="Invalid request", data=None):
        super().__init__(self.code, message, data)


class MethodNotFound(JsonRpcError):
    """Error raised when requested method is not found."""
    code = -32601

    def __init__(self, message="Method not found", data=None):
        super().__init__(self.code, message, data)


class InvalidParams(JsonRpcError):
    """Error raised when incorect params are used for method call."""
    code = -32602

    def __init__(self, message="Invalid params", data=None):
        super().__init__(self.code, message, data)


class InternalError(JsonRpcError):
    """Error raised for JSON-RPC implementation related errors."""
    code = -32603

    def __init__(self, message="Internal error", data=None):
        super().__init__(self.code, message, data)


class ApplicationError(JsonRpcError):
    """Errors raised by application (called methods) should inherit from this."""
    def __init__(self, code, message="Application error", data=None):
        if -32000 >= code >= -32768:
            raise ValueError("Error codes between -32000 and -32768 are reserved by JSON-RPC 2.0 specification.")

        super().__init__(code, message, data)


class Response(object, metaclass=abc.ABCMeta):
    """Base for JSON-RPC responses.

    Attributes:
        request (Request): Request this is a response for.
    """

    def __init__(self, request):
        """
        Args:
            request (Request): Request this is a response for.
        """
        self.request = request

    @property
    @abc.abstractmethod
    def dict(self):
        """Return response as dict.

        Returns:
            dict
        """
        pass

    @property
    def body(self):
        """Return response as string, for notifications empty string.

        Returns:
            str
        """
        if self.request.is_notification:
            return ""
        else:
            return json.dumps(self.dict)


class ErrorResponse(Response):
    """JSON-RPC error response.

    Attributes:
        request (Request): Request this is a response for.
        code (int): Error code.
        message (str): Error message.
        data (Any): Arbitrary user data about the error.
    """

    def __init__(self, request, code, message, data=None, exc_info=True):
        """
        Args:
            request (Request): Request this is a response for.
            code (int): Error code.
            message (str): Error message.
            data (Any): Arbitrary user data about the error.
        """
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
    """JSON-RPC response returned for successful request.

    Attributes:
        request (Request): Request this is a response for.
        result (Any): Any json-serializable result of method call.
    """

    def __init__(self, request, result):
        """
        Args:
            request (Request): Request this is a response for.
            result (Any): Any json-serializable result of method call.
        """
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
    """Representation of JSON-RPC request."""

    def __init__(self, *, raw_request=None, parsed_request=None):
        """
        Use either `raw_request` or `parsed_request` to initialize a Request object.

        Args:
            raw_request (str): Raw request json as a string.
            parsed_request (dict): Parsed request json.
        """
        if raw_request is None and parsed_request is None:
            raise ValueError('Either "raw_request" or "parsed_request" must be set for Request.')

        self._raw_request = raw_request
        """str|None: Raw request json, if given."""

        self._parsed_request = parsed_request
        """dict|None: Parsed request json, if given or after being parsed from `_raw_request`."""

        self._dict = None
        """dict|None: Parsed request json after being checked for correct type, used to skip repeated checks."""

    @property
    def parsed_request(self):
        """Return parsed request, parse it from raw request if necessary.

        Returns:
            dict

        Raises:
            ParseError: If parsing of raw request fails.
        """
        if self._parsed_request is None:
            try:
                self._parsed_request = json.loads(self._raw_request)
            except (TypeError, ValueError) as e:
                raise ParseError(message=str(e))

        return self._parsed_request

    @property
    def dict(self):
        """Return request as a dict.

        Raises:
            dict

        Raises:
            InvalidRequest: If parsed request is not a dict.
        """
        if self._dict is None:
            data = self.parsed_request

            if not isinstance(data, dict):
                raise InvalidRequest('Expected an object as request body. Batch requests are not supported.')

            self._dict = data

        return self._dict

    @property
    def id(self):
        """Any: `id` as specified in the request."""
        return self.dict.get('id')

    @property
    def version(self):
        """str: Value of `jsonrpc` member of the request.

        Raises:
            InvalidRequest: If `jsonrpc` member is not present.
        """
        try:
            return self.dict['jsonrpc']
        except KeyError:
            raise InvalidRequest('Missing "jsonrpc" member in request.')

    @property
    def method(self):
        """str: Name of method to be called by the request.

        Raises:
            InvalidRequest: If `method` member of request is not present or is not string.
        """
        try:
            method = self.dict['method']
        except KeyError:
            raise InvalidRequest('Missing "method" member in request.')

        if not isinstance(method, str):
            raise InvalidRequest('"method" of request must be a string.')

        return method

    @property
    def params(self):
        """list|dict|None: Parameter of call as specified in the request.

        Raises:
            InvalidRequest: If `params` are specified and are not list of dict.
        """
        if 'params' not in self.dict:
            return None

        if isinstance(self.dict['params'], (list, dict)):
            return self.dict['params']
        else:
            raise InvalidRequest('"params" of request must be either object or array if present.')

    @property
    def args(self):
        """list: List of positional arguments to be used for method call."""
        if isinstance(self.params, list):
            return self.params
        else:
            return []

    @property
    def kwargs(self):
        """dict: Dictionary of keyword arguments to be used for method call."""
        if isinstance(self.params, dict):
            return self.params
        else:
            return {}

    @property
    def is_notification(self):
        """bool: True if request has no id and thus is considered a notification.

        Request is considered a notification only if client specified protocol correctly and should know he can't expect
        response if id is not set.
        """
        try:
            return self.version == "2.0" and self.id is None
        except (InvalidRequest, ParseError):
            return False


class Service(object):
    """Provides JSON-RPC endpoint for collection of methods.

    Examples:

        >>> service = Service()
        >>>
        >>> @service.method
        >>> def hello_world():
        ...   return "Hello world."
        >>>
        >>> request = Request(raw_request='{"jsonrpc": "2.0", "id": 1, "method": "hello_world"}')
        >>> response = service.handle_request(request)
        >>> response.body
        {"jsonrpc": "2.0", "id": 1, "result": "Hello world."}
        >>> request = Request(raw_request='{"jsonrpc": "2.0", "id": 1, "method": "hello_kitty"}')
        >>> response = service.handle_request(request)
        >>> response.body
        {"jsonrpc": "2.0", "id": 1, "error": {"code": -32601, "message": "Method \"hello_kitty\" is not defined."}}

    """

    def __init__(self):
        self._methods = {}
        """dict[str,typing.Callable]: Mapping of method names to callables."""

    def method(self, method):
        """Decorate function to add it into service.

        Examples:

            Either decorate without argument to add method under it's own name:

            >>> @service.method
            >>> def foo():
            ...   return "foo"
            >>>
            >>> service.get_methods()
            {'foo': <function foo at 0x10f64ca60>}

            Or use decorator with argument to set custom name:

            >>> @service.method('feeble')
            >>> def foo():
            ...   return "foo"
            >>>
            >>> service.get_methods()
            {'feeble': <function foo at 0x10f64ca60>}

        Args:
            method (typing.Callable|str): Either a method itself or method name that should be used for decorated
                method.
        """
        if callable(method):
            self.add_method(method.__name__, method)

            return method
        else:
            def wrapper(func):
                self.add_method(method, func)
                return func

            return wrapper

    def add_method(self, method_name, func):
        """Add method to service.

        Each method must either return a json-serializable response or raise an error. Do not return instances of
        Response.

        Args:
            method_name (str): Name of method for JSON-RPC.
            func (typing.Callable): Callable to be added.
        """
        if method_name in self._methods:
            raise ValueError('Method "{}" already registered.'.format(method_name))

        self._methods[method_name] = func

    def add_methods(self, methods, prefix=''):
        """Add collection of methods to service.

        Args:
            methods (list|tuple|dict|module): Collection of methods to add.
                If `list` or `tuple` is given, adds all methods under their own names.
                If `dict` is given, will use keys as method names and values as methods.
                If `module` is given, will add all public (not prefixed with `_`) functions defined at module level.
            prefix (str): Each method name will be prefixed by this.
        """
        if isinstance(methods, (list, tuple)):
            methods = {method.__name__: method for method in methods}
        elif not isinstance(methods, dict):
            methods = {method: getattr(methods, method) for method in dir(methods) if not method.startswith('_')}

        for name, method in methods.items():
            if callable(method):
                self.add_method(prefix + name, method)

    def get_methods(self):
        """Return mapping of registered method names to callables.

        Returns:
            dict[str, typing.Callable]
        """
        return self._methods.copy()

    def handle_request(self, request):
        """Process request and return response.

        Args:
            request (Request): JSON-RPC request to be processed.

        Returns:
            Response
        """
        try:
            if request.version != "2.0":
                raise InvalidRequest('Only JSON-RPC version "2.0" is supported.')

            return SuccessResponse(request, self.call_method(request, request.method, request.args, request.kwargs))
        except JsonRpcError as e:
            return ErrorResponse(request, e.code, e.message, e.data)
        except:
            return ErrorResponse(request, -32603, "Internal error.")

    def call_method(self, request, method_name, args, kwargs):
        """Call method registered under `method_name` with given `args` and `kwargs`.

        Args:
            request (Request): Request which resulted in this method call.
            method_name (str): Name of method to call.
            args (list|tuple): Positional arguments for method call.
            kwargs (dict): Keyword arguments for method call.

        Raises:
            MethodNotFound: If method with given `method_name` is not found.
            InvalidParams: If method does not accept given `args` and `kwargs`.

        Returns:
            Any: Result of method call (must be serializable by json.dumps).
        """
        if method_name not in self._methods:
            raise MethodNotFound('Method "{}" is not defined.'.format(method_name))

        method = self._methods[method_name]

        try:
            inspect.signature(method).bind(*args, **kwargs)
        except TypeError as e:
            raise InvalidParams(str(e))

        return method(*args, **kwargs)
