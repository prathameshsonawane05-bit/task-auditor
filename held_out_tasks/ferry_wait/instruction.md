# The ferry sheet by the hall clock

The Saturday boats are written as minutes from midnight, already in order. Cal does not want anyone sorting the sheet again and "fixing" a note he wrote on purpose.

`wait_minutes(now, departures)` is how long you still have. If a boat leaves at this exact minute, the wait is zero: you are meant to be on the ramp, not drinking another cup. If a later boat is still on the sheet, the wait is that departure minus now. Boats already gone stay on the paper; they are not the answer.

When the rest of the sheet is in the past, or there is no sheet at all, return -1. That means tomorrow's pencil copy, not an error.
