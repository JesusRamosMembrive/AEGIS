from custom_math import subtract

def test_subtract():
    assert subtract(5, 3) == 2
    assert subtract(10, 7) == 3
    assert subtract(3, 5) == -2
    assert subtract(0, 0) == 0
    assert subtract(-5, -3) == -2
