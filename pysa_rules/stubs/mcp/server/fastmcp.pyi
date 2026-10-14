from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

class FastMCP:
    def __init__(self, name: str) -> None: ...
    def tool(self) -> Callable[[F], F]: ...
