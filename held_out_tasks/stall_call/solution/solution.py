def stall_summary(jars: int, price_pence: int) -> str:
    if jars < 0 or price_pence < 0:
        raise ValueError("counts and prices cannot be negative")
    return f"We set out {jars} jars and asked {price_pence} pence for each one."
