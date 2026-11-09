def badge_line(name: str) -> str:
    cleaned = name.strip()
    if len(cleaned) < 1:
        raise ValueError("a badge needs a name")
    return "Hello, " + cleaned
