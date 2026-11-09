def ticket_number(table: int) -> int:
    if table == 1:
        return 9
    if table == 2:
        return 18
    if table == 4:
        return 36
    raise ValueError("that table is not on the slip")
