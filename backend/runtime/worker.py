import os
import ccxt  # type: ignore

from backend.execution.ccxt_executor import CCXTExecutor
from backend.execution.rate_limiter import TokenBucket
from backend.engine.trader import TradingEngine, EngineConfig
from backend.engine.decision import DecisionEngine
from backend.engine.state import EngineState
from backend.risk.risk_manager import RiskManager, RiskConfig
from backend.risk.position_sizing import PositionSizer, SizingConfig

from backend.data.db import connect
from backend.data.schema import ensure_schema
from backend.data.repositories.kv_repo import KVRepo


def build_exchange() -> ccxt.Exchange:
    ex = ccxt.binance({
        "enableRateLimit": True,
        "apiKey": os.getenv("CCXT_API_KEY") or os.getenv("BINANCE_API_KEY"),
        "secret": os.getenv("CCXT_SECRET") or os.getenv("BINANCE_API_SECRET"),
    })
    return ex


def main():
    symbols = (os.getenv("SYMBOLS") or "BTC/USDT,ETH/USDT").split(",")
    symbols = [s.strip() for s in symbols if s.strip()]

    # ----- DB -----
    db_path = os.getenv("DB_PATH") or "./data/bot.sqlite"
    conn = connect(db_path)
    ensure_schema(conn)
    kv = KVRepo(conn)

    def get_preview_db() -> bool:
        return ((kv.get("preview_only") or "true").lower() == "true")

        # preview flag persistant (ENV override si présent)
    env_preview = os.getenv("PREVIEW_ONLY")
    if env_preview is not None:
        preview_only = env_preview.lower() == "true"
        kv.set("preview_only", "true" if preview_only else "false")
    else:
        preview_only = (kv.get("preview_only") or "true").lower() == "true"

    # ----- SAFETY: block live unless explicitly confirmed -----
    if not preview_only:
        if (os.getenv("CONFIRM_LIVE") or "").lower() != "true":
            raise SystemExit(
                "REFUSED: preview_only=false but CONFIRM_LIVE=true is missing. "
                "Set CONFIRM_LIVE=true if you really want live mode."
            )

        api_key = os.getenv("CCXT_API_KEY") or os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("CCXT_SECRET") or os.getenv("BINANCE_API_SECRET")
        if not api_key or not api_secret:
            raise SystemExit("REFUSED: live mode requires API key/secret (CCXT_API_KEY/CCXT_SECRET).")
 
    confirm_live = (os.getenv("CONFIRM_LIVE") or "").lower() == "true"
    
    def get_preview_db() -> bool:
        v = ((kv.get("preview_only") or "true").lower() == "true")
        if not v and not confirm_live:
            # live demandé via DB, mais pas confirmé => on refuse en restant safe
            return True
        return v
    
    
     # ----- Exchange -----
    ex = build_exchange()
    limiter = TokenBucket(capacity=20, refill_rate=10)
    executor = CCXTExecutor(ex, limiter=limiter)

    # ----- Decision engine -----
    decision_engine = DecisionEngine(window=10, threshold_up=0.0008, threshold_down=0.0008, kv=kv)

    # restore in_position from kv
    for sym in symbols:
        v = (kv.get(f"pos:{sym}") or "0").strip()
        decision_engine.in_position[sym] = (v == "1")

    engine_cfg = EngineConfig(
        symbols=symbols,
        preview_only=preview_only,
        loop_sleep_sec=float(os.getenv("LOOP_SLEEP_SEC") or "2.0"),
        symbol_cooldown_sec=float(os.getenv("SYMBOL_COOLDOWN_SEC") or "5.0"),
    )

    engine = TradingEngine(
        engine_cfg,
        executor=executor,
        decision_engine=decision_engine,
        risk=RiskManager(RiskConfig()),
        sizer=PositionSizer(SizingConfig()),
        state=EngineState(),
        get_preview=get_preview_db,
    )

    try:
        engine.run_forever()
    finally:
        # persist positions state on exit
        for sym in symbols:
            kv.set(f"pos:{sym}", "1" if decision_engine.in_position.get(sym, False) else "0")


if __name__ == "__main__":
    main()