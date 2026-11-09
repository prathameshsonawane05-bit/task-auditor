def postage_pence(grams: int) -> int:
    if grams < 0:
        raise ValueError("the scale cannot read a negative")
    if grams < 100:
        return 80
    if grams < 500:
        return 150
    if grams <= 2000:
        return 320
    raise ValueError("too heavy for the bike")
