class RateLimiter:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.used = 0

    def allow(self) -> bool:
        if self.used < self.limit:
            self.used += 1
            return True
        return False
