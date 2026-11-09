def flour_grams(cups: int) -> int:
    if cups < 0:
        raise ValueError("a cup count cannot be negative")
    return cups * 120
