from dataclasses import dataclass
from time import time


@dataclass
class RiskConfig:
    max_trades_per_hour: int = 30
    max_consecutive_errors: int = 10
    max_daily_drawdown_pct: float = 5.0
    max_total_exposure_usdt: float = 100.0
    max_symbol_exposure_usdt: float = 20.0


class RiskManager:
    def __init__(self, cfg: RiskConfig):
        self.cfg = cfg
        self._trade_timestamps: list[float] = []
        self._consecutive_errors = 0

        self._day_start_equity: float | None = None
        self._kill_switch = False

    def register_trade(self) -> None:
        now = time()
        self._trade_timestamps.append(now)
        self._trim(now)
        self._consecutive_errors = 0

    def register_error(self) -> None:
        self._consecutive_errors += 1
        if self._consecutive_errors >= self.cfg.max_consecutive_errors:
            self._kill_switch = True

    def set_day_start_equity(self, equity: float) -> None:
        self._day_start_equity = float(equity)

    def update_equity(self, equity: float) -> None:
        if self._day_start_equity is None:
            self._day_start_equity = float(equity)
            return

        dd_pct = (self._day_start_equity - float(equity)) / self._day_start_equity * 100.0
        if dd_pct >= self.cfg.max_daily_drawdown_pct:
            self._kill_switch = True

    def can_trade_now(self) -> tuple[bool, str]:
        if self._kill_switch:
            return False, "kill_switch_enabled"

        now = time()
        self._trim(now)

        if len(self._trade_timestamps) >= self.cfg.max_trades_per_hour:
            return False, "trade_rate_limited"

        return True, "ok"

    def _trim(self, now: float) -> None:
        one_hour = 3600.0
        self._trade_timestamps = [t for t in self._trade_timestamps if now - t <= one_hour]