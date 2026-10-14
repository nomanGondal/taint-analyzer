def bad_add(a:int,b:int)-> str:
    return f"{a + b}"

def print_result() -> None:
    result = bad_add(1,2)
    print(result)

if __name__ =="__main__":
    print_result()