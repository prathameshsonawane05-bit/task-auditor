# Parse a compact duration

Write `parse_duration(text)` so that it:

- adds hours, minutes, and seconds into a total number of seconds
- raises ValueError with the message bad duration when a unit has no number or the unit is unknown

`h` is 3600 seconds, `m` is 60, and `s` is 1. `1h2m3s` is 3723 seconds. There are no spaces.
