# json-rpc-service

Simple extendable JSON-RPC Service builder and handler.

## Prerequisites

This library is supposed to run with Python 3. No other dependencies are needed.

## Usage

```python
from jsonrpcservice import Service, ApplicationError, Request

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
    raise ApplicationError(1200, "It was all in vain.")


request = Request(raw_request='{"jsonrpc": "2.0", "id": 321, "method": "foo"}')
response = service.handle_request(request)
response.body  # '{"jsonrpc":"2.0","id": 321,"result":"Foo is not bar."}'

request = Request(parsed_request={"jsonrpc": "2.0", "id": 321, "method": "add", "params": {"a": 5, "b": 13}})
response = service.handle_request(request)
response.dict  # {"jsonrpc": "2.0", "id": 321, "result": 18}

request = Request(parsed_request={"jsonrpc": "2.0", "id": 321, "method": "fail"})
response = service.handle_request(request)
response.dict  # {"jsonrpc": "2.0", "id": 321, "error": {"code": 1200, "message": "It was all in vain."}}
```

For more examples and documentation see docstrings.


## Running the tests

```
python3 -m unittest
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
