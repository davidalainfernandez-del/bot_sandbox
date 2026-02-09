import time
import threading


class TokenBucket:
    """
    Rate limiter simple: tokens ajoutés à un débit constant.
    - capacity: taille du seau
    - refill_rate: tokens par seconde
    """

    def __init__(self, capacity: float, refill_rate: float):
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self._tokens = float(capacity)
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, tokens: float = 1.0, timeout: float | None = None) -> bool:
        deadline = None if timeout is None else time.monotonic() + timeout
        tokens = float(tokens)

        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self._last
                self._last = now
                self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)

                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True

            if deadline is not None and time.monotonic() > deadline:
                return False

            time.sleep(0.01)