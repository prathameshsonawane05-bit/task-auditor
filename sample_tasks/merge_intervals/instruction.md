# Merge overlapping intervals

Write `merge_intervals(intervals)` so that it:

- sorts the intervals and merges each pair that overlaps or touches
- leaves a gap when the next interval starts after the previous end

Each interval is a pair of integers `(start, end)`. Touching means the next start equals the previous end. An empty input returns an empty list.
