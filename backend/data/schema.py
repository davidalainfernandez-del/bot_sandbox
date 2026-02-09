import sqlite3
from .db import cursor


def ensure_schema(conn: sqlite3.Connection) -> None:
    with cursor(conn) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS kv(
              k TEXT PRIMARY KEY,
              v TEXT NOT NULL
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS orders(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              ts INTEGER NOT NULL,
              symbol TEXT NOT NULL,
              side TEXT NOT NULL,
              qty REAL,
              quote_qty REAL,
              price REAL,
              status TEXT,
              raw_json TEXT
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS positions(
              symbol TEXT PRIMARY KEY,
              qty REAL NOT NULL,
              avg_entry REAL,
              updated_ts INTEGER NOT NULL
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ledger(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              ts INTEGER NOT NULL,
              kind TEXT NOT NULL,
              symbol TEXT,
              amount REAL,
              meta_json TEXT
            );
            """
        )