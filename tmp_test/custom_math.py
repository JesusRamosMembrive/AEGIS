def divide(numerator, denominator):
    """
    Performs division of two numbers.

    Args:
        numerator: The number to be divided.
        denominator: The number to divide by.

    Returns:
        The result of the division.

    Raises:
        ValueError: If the denominator is zero.
    """
    if denominator == 0:
        raise ValueError("Cannot divide by zero.")
    return numerator / denominator

import math

def calculate_logarithm(number, base):
    """
    Calculates the logarithm of a number to a given base.

    Args:
        number: The number for which to calculate the logarithm.
        base: The base of the logarithm.

    Returns:
        The logarithm of the number to the given base.

    Raises:
        ValueError: If the number is non-positive or the base is not positive and not equal to 1.
    """
    if number <= 0:
        raise ValueError("Number must be positive.")
    if base <= 0 or base == 1:
        raise ValueError("Base must be positive and not equal to 1.")
    return math.log(number, base)