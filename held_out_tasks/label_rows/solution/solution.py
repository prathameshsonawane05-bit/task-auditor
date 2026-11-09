def pack_rows(labels: list[str], width: int) -> list[list[str]]:
    if width < 1:
        raise ValueError("a row needs at least one slot")
    rows: list[list[str]] = []
    start = 0
    while start < len(labels):
        rows.append(labels[start : start + width])
        start += width
    return rows
