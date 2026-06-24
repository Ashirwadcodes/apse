import json
import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from backend.models.technology import Technology

logger = logging.getLogger(__name__)

_DB_PATH = Path(__file__).parent / "cache.db"


def _serialize(value: Any) -> str:
    results, source_totals = value
    return json.dumps({
        "results": [r.model_dump(mode="json") for r in results],
        "source_totals": source_totals,
    }, default=str)


def _deserialize(raw: str) -> Any:
    data = json.loads(raw)
    results = [Technology(**r) for r in data["results"]]
    return results, data["source_totals"]


class TTLCache:
    def __init__(self, db_path: Path = _DB_PATH):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS cache "
            "(key TEXT PRIMARY KEY, value TEXT NOT NULL, expires_at REAL NOT NULL)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_expires ON cache(expires_at)"
        )
        self._conn.commit()
        self._purge_expired()
        logger.info("SQLite cache ready at %s", db_path)

    def _purge_expired(self) -> None:
        self._conn.execute("DELETE FROM cache WHERE expires_at <= ?", (time.time(),))
        self._conn.commit()

    def get(self, key: str) -> Any:
        with self._lock:
            row = self._conn.execute(
                "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
            ).fetchone()
            if row is None:
                return None
            raw, expires_at = row
            if time.time() > expires_at:
                self._conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                self._conn.commit()
                return None
            try:
                return _deserialize(raw)
            except Exception as e:
                logger.warning("Cache deserialize failed for key %s — %s", key, e)
                self._conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                self._conn.commit()
                return None

    def set(self, key: str, value: Any, ttl: int = 86400) -> None:
        with self._lock:
            try:
                raw = _serialize(value)
                expires_at = time.time() + ttl
                self._conn.execute(
                    "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
                    (key, raw, expires_at),
                )
                self._conn.commit()
            except Exception as e:
                logger.warning("Cache write failed — %s", e)

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            self._conn.commit()

    def clear(self) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM cache")
            self._conn.commit()


cache = TTLCache()
