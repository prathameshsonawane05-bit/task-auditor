def jar_total(lines: list[tuple[str, int]], jar: str) -> int:
    total = 0
    for name, count in lines:
        if name == jar:
            total += count
    return total
