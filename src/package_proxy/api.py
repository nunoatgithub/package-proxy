from typing import Protocol, Any


class ProxyApi(Protocol):

    def get_module(self, fullname) -> int:
        ...

    def get_attr(self, proxy_id, item) -> Any:
        ...

    def set_attr(self, proxy_id, key, value) -> Any:
        ...

    def call(self, proxy_id, method, *args, **kwargs) -> Any:
        ...
