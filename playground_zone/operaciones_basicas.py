"""
Operaciones Basicas - Las cuatro operaciones matematicas fundamentales
"""

import math


def suma(a: float, b: float) -> float:
    """Suma dos numeros."""
    return a + b


def resta(a: float, b: float) -> float:
    """Resta el segundo numero del primero."""
    return a - b


def multiplicacion(a: float, b: float) -> float:
    """Multiplica dos numeros."""
    return a * b


def division(a: float, b: float) -> float:
    """Divide el primer numero entre el segundo.

    Raises:
        ValueError: Si el divisor es cero.
    """
    if b == 0:
        raise ValueError("No se puede dividir entre cero")
    return a / b


def raiz_cuadrada(a: float) -> float:
    """Calcula la raiz cuadrada de un numero.

    Args:
        a: Numero del cual calcular la raiz cuadrada.

    Returns:
        La raiz cuadrada del numero.

    Raises:
        ValueError: Si el numero es negativo.
    """
    if a < 0:
        raise ValueError("No se puede calcular la raiz cuadrada de un numero negativo")
    return math.sqrt(a)


def logaritmo(a: float, base: float = math.e) -> float:
    """Calcula el logaritmo de un numero en una base especificada.

    Args:
        a: Numero del cual calcular el logaritmo.
        base: Base del logaritmo (por defecto e para logaritmo natural).

    Returns:
        El logaritmo del numero en la base especificada.

    Raises:
        ValueError: Si el numero es menor o igual a cero.
        ValueError: Si la base es menor o igual a cero, o igual a uno.
    """
    if a <= 0:
        raise ValueError("No se puede calcular el logaritmo de un numero menor o igual a cero")
    if base <= 0 or base == 1:
        raise ValueError("La base debe ser mayor que cero y distinta de uno")
    return math.log(a, base)


def logaritmo_natural(a: float) -> float:
    """Calcula el logaritmo natural (base e) de un numero.

    Args:
        a: Numero del cual calcular el logaritmo natural.

    Returns:
        El logaritmo natural del numero.

    Raises:
        ValueError: Si el numero es menor o igual a cero.
    """
    if a <= 0:
        raise ValueError("No se puede calcular el logaritmo de un numero menor o igual a cero")
    return math.log(a)


def logaritmo_base10(a: float) -> float:
    """Calcula el logaritmo en base 10 de un numero.

    Args:
        a: Numero del cual calcular el logaritmo en base 10.

    Returns:
        El logaritmo en base 10 del numero.

    Raises:
        ValueError: Si el numero es menor o igual a cero.
    """
    if a <= 0:
        raise ValueError("No se puede calcular el logaritmo de un numero menor o igual a cero")
    return math.log10(a)


def saludo(despedida: bool = False) -> str:
    """Dice hola o adios.

    Args:
        despedida: Si es True, dice adios. Si es False, dice hola.

    Returns:
        Mensaje de saludo o despedida.
    """
    return "Adios!" if despedida else "Hola!"


def foo(x: int = 42) -> str:
    """Funcion de prueba tipo foo.

    Args:
        x: Un numero cualquiera (por defecto 42).

    Returns:
        Un string con el valor recibido.
    """
    return f"foo dice: {x}"


def foo_2() -> str:
    """Dice hola mundo."""
    return "Hola mundo"


def foo_4(start_num: int):
    """Realiza una cuenta atras desde start_num hasta 5."""
    for i in range(start_num, 4, -1):
        print(i)


def foo_6() -> None:
    """Cuenta del 1 al 5."""
    for i in range(1, 6):
        print(i)


if __name__ == "__main__":
    # Ejemplos de uso
    print(f"Suma: 10 + 5 = {suma(10, 5)}")
    print(f"Resta: 10 - 5 = {resta(10, 5)}")
    print(f"Multiplicacion: 10 * 5 = {multiplicacion(10, 5)}")
    print(f"Division: 10 / 5 = {division(10, 5)}")
    print(f"Raiz cuadrada: sqrt(16) = {raiz_cuadrada(16)}")
    print(f"Logaritmo natural: ln(e) = {logaritmo_natural(math.e)}")
    print(f"Logaritmo base 10: log10(100) = {logaritmo_base10(100)}")
    print(f"Logaritmo base 2: log2(8) = {logaritmo(8, 2)}")
