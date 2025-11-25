from typing import Protocol, Any


class ProxyApi(Protocol):

    def get_module(self, fullname: str) -> int:
        ...

    def get_attr(self, proxy_id: int, item: str) -> Any:
        ...

    def set_attr(self, proxy_id: int, key: str, value: Any) -> Any:
        ...

    def create_object(self, parent_id: int, cls_name: str, *args: Any, **kwargs: Any) -> int:
        ...

    def call(self, proxy_id: int, func_name: str, *args: Any, **kwargs: Any) -> Any:
        ...