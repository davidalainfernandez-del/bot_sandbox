from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

import ccxt  # type: ignore

from .rate_limiter import TokenBucket
from .errors import ExecutionError, RateLimitError, ExchangeRejectedOrder, InsufficientFunds
from .precision import extract_limits, check_min_notional, round_amount


@dataclass
class OrderResult:
    order_id: str | None
    symbol: str
    side: str
    status: str
    filled: float | None
    average: float | None
    cost: float | None
    raw: dict[str, Any]


class CCXTExecutor:
    """
    Wrapper CCXT:
    - cache markets
    - rate limiter central
    - validation minNotional/precision
    - retry réseau / ratelimit
    """

    def __init__(
        self,
        exchange: ccxt.Exchange,
        *,
        limiter: TokenBucket | None = None,
        max_retries: int = 3,
        retry_sleep: float = 0.5,
    ):
        self.ex = exchange
        self.limiter = limiter or TokenBucket(capacity=10, refill_rate=5)
        self.max_retries = max_retries
        self.retry_sleep = retry_sleep
        self._markets: dict[str, Any] | None = None

    def load_markets_cached(self) -> dict[str, Any]:
        if self._markets is None:
            self._acquire()
            self._markets = self.ex.load_markets()
        return self._markets

    def get_market(self, symbol: str) -> dict[str, Any]:
        markets = self.load_markets_cached()
        if symbol not in markets:
            raise ExecutionError(f"Unknown symbol: {symbol}")
        return markets[symbol]

    def fetch_ticker(self, symbol: str) -> dict[str, Any]:
        return self._call(lambda: self.ex.fetch_ticker(symbol))

    def fetch_balance(self) -> dict[str, Any]:
        return self._call(lambda: self.ex.fetch_balance())

    def place_market_buy_quote(self, symbol: str, quote_amount: float) -> OrderResult:
        """
        Achat market "pour X quote" (ex: X USDT) via quoteOrderQty quand supporté.
        """
        if quote_amount <= 0:
            raise ExchangeRejectedOrder("quote_amount must be > 0")

        market = self.get_market(symbol)
        limits = extract_limits(market)

        # Sur un buy market avec quoteOrderQty, le notional = quote_amount (approx)
        if not check_min_notional(limits.min_notional, quote_amount):
            raise ExchangeRejectedOrder(f"minNotional fail: {quote_amount} < {limits.min_notional}")

        params = {"quoteOrderQty": quote_amount}
        raw = self._call(lambda: self.ex.create_order(symbol, "market", "buy", None, None, params))

        return OrderResult(
            order_id=raw.get("id"),
            symbol=symbol,
            side="buy",
            status=str(raw.get("status") or "unknown"),
            filled=raw.get("filled"),
            average=raw.get("average"),
            cost=raw.get("cost"),
            raw=raw,
        )

    def place_market_sell_base(self, symbol: str, base_amount: float) -> OrderResult:
        if base_amount <= 0:
            raise ExchangeRejectedOrder("base_amount must be > 0")

        market = self.get_market(symbol)
        limits = extract_limits(market)

        base_amount = round_amount(base_amount, limits.amount_precision)

        if limits.min_amount is not None and base_amount < float(limits.min_amount):
            raise ExchangeRejectedOrder(f"minAmount fail: {base_amount} < {limits.min_amount}")

        raw = self._call(lambda: self.ex.create_order(symbol, "market", "sell", base_amount, None, {}))

        return OrderResult(
            order_id=raw.get("id"),
            symbol=symbol,
            side="sell",
            status=str(raw.get("status") or "unknown"),
            filled=raw.get("filled"),
            average=raw.get("average"),
            cost=raw.get("cost"),
            raw=raw,
        )

    # ---------------- internals ----------------

    def _acquire(self) -> None:
        ok = self.limiter.acquire(1.0, timeout=5.0)
        if not ok:
            raise RateLimitError("Rate limiter timeout")

    def _call(self, fn: Callable[[], Any]):
        last_err: Exception | None = None

        for _ in range(self.max_retries):
            try:
                self._acquire()
                return fn()

            except ccxt.InsufficientFunds as e:
                raise InsufficientFunds(str(e)) from e

            except ccxt.InvalidOrder as e:
                raise ExchangeRejectedOrder(str(e)) from e

            except ccxt.RateLimitExceeded as e:
                last_err = e
                time.sleep(self.retry_sleep)

            except ccxt.NetworkError as e:
                last_err = e
                time.sleep(self.retry_sleep)

            except Exception as e:
                last_err = e
                time.sleep(self.retry_sleep)

        raise ExecutionError(f"CCXT call failed after retries: {last_err}") from last_err
    