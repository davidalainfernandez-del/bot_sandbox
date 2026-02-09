import time
import logging
from dataclasses import dataclass
from typing import Callable, Optional

from .state import EngineState
from .decision import DecisionEngine
from ..execution.ccxt_executor import CCXTExecutor
from ..risk.risk_manager import RiskManager
from ..risk.position_sizing import PositionSizer


@dataclass
class EngineConfig:
    symbols: list[str]
    loop_sleep_sec: float = 2.0
    symbol_cooldown_sec: float = 5.0
    preview_only: bool = True


class TradingEngine:
    def __init__(
        self,
        cfg: EngineConfig,
        *,
        executor: CCXTExecutor,
        decision_engine: DecisionEngine,
        risk: RiskManager,
        sizer: PositionSizer,
        state: EngineState | None = None,
        get_preview: Optional[Callable[[], bool]] = None,
    ):
        self.cfg = cfg
        self.executor = executor
        self.decision_engine = decision_engine
        self.risk = risk
        self.sizer = sizer
        self.state = state or EngineState()
        self._running = False
        self.log = logging.getLogger("engine")
        self.get_preview = get_preview

    def run_forever(self) -> None:
        logging.basicConfig(level=logging.INFO)
        self.log.info(
            "Engine started: preview_only=%s symbols=%s",
            self.cfg.preview_only,
            self.cfg.symbols,
        )

        self._running = True
        try:
            while self._running:
                for symbol in self.cfg.symbols:
                    self._tick_symbol(symbol)
                time.sleep(self.cfg.loop_sleep_sec)
        except KeyboardInterrupt:
            self.log.info("Engine stopped by user (CTRL+C)")
            self._running = False

    def stop(self) -> None:
        self._running = False

    def _is_preview(self) -> bool:
        if self.get_preview is None:
            return self.cfg.preview_only
        try:
            return bool(self.get_preview())
        except Exception:
            # si la DB est temporairement indispo, on repasse en mode safe
            return True

    def _tick_symbol(self, symbol: str) -> None:
        st = self.state.get(symbol)

        if self.state.in_cooldown(symbol):
            return

        with st.lock:
            ok, reason = self.risk.can_trade_now()
            if not ok:
                st.last_error = reason
                return

            try:
                ticker = self.executor.fetch_ticker(symbol)
                ctx = {"ticker": ticker}

                decision = self.decision_engine.decide(symbol, ctx)
                st.last_signal = f"{decision.action}:{decision.reason}"

                self.log.info(
                    "%s price=%s decision=%s (%s)",
                    symbol,
                    ticker.get("last"),
                    decision.action,
                    decision.reason,
                )

                if decision.action == "hold":
                    return

                # HOT: preview state (DB)
                if self._is_preview():
                    self.risk.register_trade()
                    self.state.set_cooldown(symbol, self.cfg.symbol_cooldown_sec)
                    return

                # LIVE
                if decision.action == "buy":
                    quote = self.sizer.compute_quote_amount(signal_strength=decision.strength)
                    self.executor.place_market_buy_quote(symbol, quote)
                    self.risk.register_trade()
                    self.state.set_cooldown(symbol, self.cfg.symbol_cooldown_sec)

                elif decision.action == "sell":
                    # TODO: récupérer qty position réelle via DB/portfolio
                    return

            except Exception as e:
                st.last_error = str(e)
                self.risk.register_error()
                self.state.set_cooldown(symbol, self.cfg.symbol_cooldown_sec)