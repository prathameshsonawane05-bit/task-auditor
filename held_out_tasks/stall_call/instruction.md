# Shouting the stall open

When the stall opens, somebody has to call a summary the other volunteers can hear from the tea urn. `stall_summary(jars, price_pence)` is that call. It should say how many jars were set out and what price, in pence, was asked for each one. Zero jars is a real morning. Say so rather than pretending the table is full.

A negative jar count or a negative price is a miscount from the cash tin. Raise ValueError and say "counts and prices cannot be negative".
