def even_or_odd(numbers: list) -> dict:
    """
    Determines if a number is even or odd, add a list and return.
    :param number: Description
    :return: Description
    :rtype: list
    """
    dict_of_results = {}
    for number in numbers:
        if number % 2 == 0:
            dict_of_results[number] = "even"
        else:
            dict_of_results[number] = "odd"
    return dict_of_results

if __name__ == "__main__":

    sample_numbers = [1, 2, 3, 4, 5, 6]
    results = even_or_odd(sample_numbers)
    print(results)
