# Name cards on the trestle tables

Before the doors open, Jo walks the trestles and lays the name cards in rows. The width is however many cards fit on that table tonight. It changes. Last week it was two. The kids' table only ever fits one.

`pack_rows(labels, width)` keeps the order Jo was given. It fills a row, starts the next row, and does not invent blank cards to square off the end. An empty list of labels is an empty layout, even when the width is generous.

Zero slots, or a negative width, is Jo holding the tape measure backwards. Raise ValueError and say "a row needs at least one slot".
