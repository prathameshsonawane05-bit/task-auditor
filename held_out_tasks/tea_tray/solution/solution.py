def sugar_spoons(kind: str, spoons: int) -> int:
    if kind == "sweet":
        return spoons * 2
    if kind == "plain":
        return spoons
    raise ValueError("tea is sweet or plain")
