import os
from flask import Blueprint, jsonify, request

from backend.data.db import connect
from backend.data.schema import ensure_schema
from backend.data.repositories.kv_repo import KVRepo

bp = Blueprint("admin", __name__)


def _kv() -> KVRepo:
    db_path = os.getenv("DB_PATH") or "./data/bot.sqlite"
    conn = connect(db_path)
    ensure_schema(conn)
    return KVRepo(conn)


@bp.post("/admin/preview")
def set_preview():
    body = request.get_json(silent=True) or {}
    preview = bool(body.get("preview", True))

    kv = _kv()
    kv.set("preview_only", "true" if preview else "false")

    return jsonify({"preview": preview, "saved": True})


@bp.get("/admin/preview")
def get_preview():
    kv = _kv()
    v = (kv.get("preview_only") or "true").lower() == "true"
    return jsonify({"preview": v})

@bp.get("/admin/positions")
def get_positions():
    kv = _kv()

    # On lit les positions connues (limité à BTC/ETH pour l’instant)
    # Plus tard: on aura une table positions ou une liste symbols en kv
    out = {}
    for sym in ["BTC/USDT", "ETH/USDT"]:
        out[sym] = (kv.get(f"pos:{sym}") or "0") == "1"

    return jsonify({"positions": out})