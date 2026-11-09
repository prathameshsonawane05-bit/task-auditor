def kettle_seconds(mugs: int) -> int:
    if mugs < 1:
        raise ValueError("brew at least one mug")
    return mugs * 120
