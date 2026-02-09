from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SymbolLimits:
    min_notional: float | None
    min_amount: float | None
    amount_precision: int | None
    price_precision: int | None


def extract_limits(market: dict[str, Any]) -> SymbolLimits:
    limits = market.get("limits") or {}
    cost = limits.get("cost") or {}
    amount = limits.get("amount") or {}
    precision = market.get("precision") or {}

    return SymbolLimits(
        min_notional=cost.get("min"),
        min_amount=amount.get("min"),
        amount_precision=precision.get("amount"),
        price_precision=precision.get("price"),
    )


def check_min_notional(min_notional: float | None, notional: float) -> bool:
    if min_notional is None:
        return True
    return notional >= float(min_notional)


def round_amount(amount: float, amount_precision: int | None) -> float:
    if amount_precision is None:
        return float(amount)
    return round(float(amount), int(amount_precision))