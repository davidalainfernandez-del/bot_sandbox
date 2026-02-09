from __future__ import annotations

from dataclasses import dataclass
from collections import deque
from typing import Optional


@dataclass
class Decision:
    action: str  # "buy", "sell", "hold"
    reason: str
    strength: float = 0.5


class DecisionEngine:
    """
    Stratégie momentum simple + persistance de in_position dans KV.
    """

    def __init__(
        self,
        window: int = 10,
        threshold_up: float = 0.0008,
        threshold_down: float = 0.0008,
        kv: Optional[object] = None,  # attend un objet avec .get/.set (KVRepo)
    ):
        self.window = int(window)
        self.threshold_up = float(threshold_up)
        self.threshold_down = float(threshold_down)
        self.prices: dict[str, deque[float]] = {}
        self.in_position: dict[str, bool] = {}
        self.kv = kv

    def _persist_pos(self, symbol: str) -> None:
        if self.kv is None:
            return
        self.kv.set(f"pos:{symbol}", "1" if self.in_position.get(symbol, False) else "0")

    def decide(self, symbol: str, ctx: dict) -> Decision:
        last = ctx.get("ticker", {}).get("last")
        if last is None:
            return Decision(action="hold", reason="no_price", strength=0.0)

        price = float(last)
        dq = self.prices.get(symbol)
        if dq is None:
            dq = deque(maxlen=self.window)
            self.prices[symbol] = dq

        dq.append(price)

        if len(dq) < self.window:
            return Decision(action="hold", reason="warmup", strength=0.0)

        p0 = dq[0]
        if p0 <= 0:
            return Decision(action="hold", reason="bad_price0", strength=0.0)

        change = (price - p0) / p0
        pos = self.in_position.get(symbol, False)

        if (not pos) and change >= self.threshold_up:
            self.in_position[symbol] = True
            self._persist_pos(symbol)
            strength = min(1.0, change / (self.threshold_up * 3.0))
            return Decision(action="buy", reason=f"momentum_up {change:.5f}", strength=strength)

        if pos and change <= -self.threshold_down:
            self.in_position[symbol] = False
            self._persist_pos(symbol)
            strength = min(1.0, abs(change) / (self.threshold_down * 3.0))
            return Decision(action="sell", reason=f"momentum_down {change:.5f}", strength=strength)

        return Decision(action="hold", reason=f"flat {change:.5f}", strength=0.2)