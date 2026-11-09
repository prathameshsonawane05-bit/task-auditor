def wait_minutes(now: int, departures: list[int]) -> int:
    for departure in departures:
        if departure >= now:
            return departure - now
    return -1
