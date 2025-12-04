def add(*args):
    return sum(args)

def multiply(*args):
    result = 1
    for n in args:
        result *= n
    return result

def subtract(a, b):
    return a - b
