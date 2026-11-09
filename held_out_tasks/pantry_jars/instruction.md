# The pantry list on the fridge

Priya keeps a pencil list of what went into the jars and what came out. A line is a name and a count. Taking something out is a negative count, not a separate kind of line. Capital letters are a different jar: "Oats" is not "oats", and Priya has been bitten by that before.

`jar_total(lines, jar)` adds only the lines whose name is exactly the jar she asked about. If that name never appears, or the list is empty, the total is zero. She does not want a missing jar to look like an error. It is just an empty jar.
