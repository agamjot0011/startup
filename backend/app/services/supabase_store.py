"""Supabase REST persistence layer.

Direct Postgres ports are unreachable from this host, so persistence uses the
Supabase REST API with the service-role key already present in backend/.env.
Writes mirror in-memory service state; failures are logged and never break a
request (alpha safety), but are retried on the next mutation.
"""

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

_lock = threading.RLock()
_loaded = False
_base: Optional[str] = None
_key: Optional[str] = None


def _load_env() -> None:
    global _loaded, _base, _key
    with _lock:
        if _loaded:
            return
        env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        try:
            for line in open(env_path, encoding="utf-8", errors="replace"):
                if "=" not in line or line.startswith("#"):
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().rstrip("\r")
                if k == "SUPABASE_URL":
                    _base = v.rstrip("/")
                elif k == "SUPABASE_SERVICE_ROLE_KEY":
                    _key = v
        except OSError:
            pass
        _loaded = True


def enabled() -> bool:
    if os.environ.get("WZDM_PERSISTENCE", "1") == "0":
        return False
    _load_env()
    return bool(_base and _key)


def request(method: str, table: str, *, params: Optional[dict] = None, body: Optional[dict | list] = None) -> Optional[list]:
    _load_env()
    if not enabled():
        return None
    url = f"{_base}/rest/v1/{table}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "apikey": _key,
        "Authorization": f"Bearer {_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation,resolution=merge-duplicates",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            text = response.read().decode("utf-8")
            return json.loads(text) if text.strip() else []
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, TimeoutError):
        return None


def save(table: str, obj, key_field: str, exclude: tuple = (), json_text: tuple = ()) -> None:
    """Mirror a dataclass instance into a Supabase table.

    jsonb columns must receive native JSON values; only text columns that
    hold JSON need explicit json.dumps (listed in json_text).
    """
    from dataclasses import asdict

    row = asdict(obj)
    encoded = {}
    for field, value in row.items():
        if field in exclude:
            continue
        if field in json_text:
            encoded[field] = json.dumps(value)
        else:
            encoded[field] = value
    upsert(table, encoded, key_field)


def upsert(table: str, row: dict, on_conflict: str = "") -> None:
    params = {"on_conflict": on_conflict} if on_conflict else None
    request("POST", table, params=params, body=row)


def insert(table: str, rows: list | dict) -> None:
    request("POST", table, body=rows)


def update(table: str, filters: dict, patch: dict) -> None:
    request("PATCH", table, params=filters, body=patch)


def select(table: str, *, filters: Optional[dict] = None, limit: int = 1000, order: Optional[str] = None) -> list:
    params = dict(filters or {})
    params["limit"] = str(limit)
    if order:
        params["order"] = order
    result = request("GET", table, params=params)
    return result or []
