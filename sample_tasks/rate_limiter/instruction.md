# Allow a fixed number of calls

Write `RateLimiter(limit)` with `allow()` so that it:

- allows a call while the number already used is below the limit, then counts that call
- rejects a call when the limit is already used up, including a limit of zero

`allow()` returns true for an allowed call and false for a rejected call.
