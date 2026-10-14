"""Simple test file to verify Pyre and Pysa work."""

def unsafe_eval(user_input: str) -> None:
    """This should trigger security issues."""
    result = eval(user_input)  # SECURITY: eval is dangerous
    print(result)

def type_error_test(value: str) -> int:
    """This has a type mismatch."""
    return value  # ERROR: returning str instead of int

def test_none_access(data) -> None:
    """This accesses None without checking."""
    x = data.get("key")  # data could be None
    print(x.upper())  # x could be None

if __name__ == "__main__":
    unsafe_eval("1 + 1")
    type_error_test("hello")
    test_none_access(None)
