def fine_pence(days_late: int) -> int:
    if days_late < 0:
        raise ValueError("a book cannot be late a negative number of days")
    if days_late < 7:
        return 25 * days_late
    return 200
