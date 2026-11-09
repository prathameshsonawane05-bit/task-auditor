def slugify(text: str) -> str:
    slug_chars: list[str] = []
    previous_was_hyphen = False
    for char in text.casefold():
        if char.isalnum():
            slug_chars.append(char)
            previous_was_hyphen = False
        elif not previous_was_hyphen:
            slug_chars.append("-")
            previous_was_hyphen = True
    return "".join(slug_chars).strip("-")
