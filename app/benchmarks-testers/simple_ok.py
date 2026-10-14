def add(a:int, b:int) -> int:
    return a + b

def do_greet(name:str)->str:
    return f"Hello, {name}!"


if __name__ == "__main__":
    name = "Ali Hassan"
    numberOne = 89992
    numberTwo = 9992
    total = add(numberOne,numberTwo)
    veryInitialMessage = do_greet(name)
    print(veryInitialMessage)
    print("Your sample total = ",total)