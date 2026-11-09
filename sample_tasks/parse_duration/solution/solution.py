def parse_duration(text: str) -> int:
    total = 0
    number = ""
    units = {"h": 3600, "m": 60, "s": 1}
    for char in text:
        if char.isdigit():
            number += char
            continue
        if char not in units:
            raise ValueError("bad duration")
        if number == "":
            raise ValueError("bad duration")
        total += int(number) * units[char]
        number = ""
    if number != "":
        raise ValueError("bad duration")
    return total
