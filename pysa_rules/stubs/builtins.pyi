from typing import Any, Optional, Union

def eval(
    __source: Union[str, bytes, bytearray],
    __globals: Optional[dict] = None,
    __locals: Optional[dict] = None,
) -> Any: ...

def exec(
    __object: Union[str, bytes, bytearray],
    __globals: Optional[dict] = None,
    __locals: Optional[dict] = None,
) -> None: ...

def compile(
    __source: Union[str, bytes, bytearray],
    __filename: str,
    __mode: str,
) -> Any: ...

def open(
    __file: Union[str, bytes, int],
    __mode: str = "r",
) -> Any: ...

def __import__(
    __name: str,
    __globals: Optional[dict] = None,
    __locals: Optional[dict] = None,
) -> Any: ...
