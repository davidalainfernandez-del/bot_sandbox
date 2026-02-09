import sqlite3
from ..db import cursor


class KVRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get(self, key: str) -> str | None:
        with cursor(self.conn) as cur:
            cur.execute("SELECT v FROM kv WHERE k = ?", (key,))
            row = cur.fetchone()
            return None if row is None else str(row["v"])

    def set(self, key: str, value: str) -> None:
        with cursor(self.conn) as cur:
            cur.execute(
                "INSERT INTO kv(k, v) VALUES(?, ?) "
                "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                (key, value),
            )