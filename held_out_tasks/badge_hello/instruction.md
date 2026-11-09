# The welcome desk badge

People write their names with a trailing space, or a whole line of nothing. The badge should still read like a person. `badge_line(name)` trims the ends and then answers with the words Hello, and the name. " Ada " is the same badge as "Ada". A single letter is still a name.

If nothing is left after the trim, there is nobody to greet. Raise ValueError and say "a badge needs a name".
