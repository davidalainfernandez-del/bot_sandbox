from dataclasses import dataclass


@dataclass
class SizingConfig:
    base_order_usdt: float = 10.0
    min_order_usdt: float = 5.0
    max_order_usdt: float = 20.0


class PositionSizer:
    def __init__(self, cfg: SizingConfig):
        self.cfg = cfg

    def compute_quote_amount(self, *, signal_strength: float = 1.0) -> float:
        # signal_strength attendu [0..1] — clamp
        s = max(0.0, min(1.0, float(signal_strength)))
        amt = self.cfg.min_order_usdt + s * (self.cfg.max_order_usdt - self.cfg.min_order_usdt)
        return float(amt)