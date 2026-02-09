from dataclasses import dataclass, field
import threading
import time


@dataclass
class SymbolRuntimeState:
    lock: threading.Lock = field(default_factory=threading.Lock)
    cooldown_until: float = 0.0
    last_error: str | None = None
    last_signal: str | None = None


class EngineState:
    def __init__(self):
        self._by_symbol: dict[str, SymbolRuntimeState] = {}
        self._global_lock = threading.Lock()

    def get(self, symbol: str) -> SymbolRuntimeState:
        with self._global_lock:
            if symbol not in self._by_symbol:
                self._by_symbol[symbol] = SymbolRuntimeState()
            return self._by_symbol[symbol]

    def in_cooldown(self, symbol: str) -> bool:
        st = self.get(symbol)
        return time.time() < st.cooldown_until

    def set_cooldown(self, symbol: str, seconds: float) -> None:
        st = self.get(symbol)
        st.cooldown_until = time.time() + float(seconds)
        