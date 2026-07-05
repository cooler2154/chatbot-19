# config/skills_db.py
import json
import os
import sqlite3
import threading
from typing import Any, Dict, List, Optional

try:
    from cryptography.fernet import Fernet, InvalidToken
except Exception:
    Fernet = None

DB_PATH = os.environ.get("SKILLS_DB_PATH", "config/skills.db")
JSON_SEED_PATH = os.environ.get("SKILLS_JSON_SEED", "config/skills.json")
_KEY_ENV = os.environ.get("SKILLS_DB_KEY")
_LOCK = threading.Lock()


def _get_fernet():
    if not _KEY_ENV or Fernet is None:
        return None
    try:
        return Fernet(_KEY_ENV.encode() if isinstance(_KEY_ENV, str) else _KEY_ENV)
    except Exception:
        return None


FERNET = _get_fernet()


def _connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _LOCK:
        conn = _connect()
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS skills (
                name TEXT PRIMARY KEY,
                display_name TEXT,
                system_prompt TEXT,
                allowed_tools TEXT,
                model TEXT,
                jde_overrides BLOB,
                default_plant TEXT,
                route TEXT,
                meta TEXT
            )
            """
        )
        conn.commit()
        conn.close()


def _encrypt(plain: str) -> bytes:
    if FERNET:
        return FERNET.encrypt(plain.encode("utf-8"))
    return plain.encode("utf-8")


def _decrypt(blob: bytes) -> str:
    if not blob:
        return ""
    if FERNET:
        try:
            return FERNET.decrypt(blob).decode("utf-8")
        except InvalidToken:
            try:
                return blob.decode("utf-8")
            except Exception:
                return ""
    try:
        return blob.decode("utf-8")
    except Exception:
        return ""


def migrate_from_json(json_path: Optional[str] = None):
    json_path = json_path or JSON_SEED_PATH
    if not os.path.exists(json_path):
        return
    with open(json_path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except Exception:
            return
    if not isinstance(data, list):
        return
    init_db()
    conn = _connect()
    cur = conn.cursor()
    for s in data:
        name = s.get("name")
        if not name:
            continue
        cur.execute("SELECT 1 FROM skills WHERE name = ?", (name,))
        if cur.fetchone():
            continue
        jde_overrides = s.get("jde_overrides", {}) or {}
        jde_json = json.dumps(jde_overrides)
        jde_blob = _encrypt(jde_json)
        allowed_tools = json.dumps(s.get("allowed_tools")) if s.get("allowed_tools") is not None else None
        meta = json.dumps({k: v for k, v in s.items() if k not in ("name","display_name","system_prompt","allowed_tools","model","jde_overrides","default_plant","route")})
        cur.execute(
            "INSERT INTO skills (name, display_name, system_prompt, allowed_tools, model, jde_overrides, default_plant, route, meta) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                name,
                s.get("display_name") or name,
                s.get("system_prompt") or "",
                allowed_tools,
                s.get("model"),
                jde_blob,
                s.get("default_plant") or "",
                s.get("route") or f"/skill/{name}/chat",
                meta,
            ),
        )
    conn.commit()
    conn.close()


def _row_to_skill(row: sqlite3.Row) -> Dict[str, Any]:
    jde_blob = row["jde_overrides"]
    jde_text = _decrypt(jde_blob) if jde_blob is not None else ""
    try:
        jde_overrides = json.loads(jde_text) if jde_text else {}
    except Exception:
        jde_overrides = {}
    allowed_tools = None
    if row["allowed_tools"]:
        try:
            allowed_tools = json.loads(row["allowed_tools"])
        except Exception:
            allowed_tools = None
    meta = {}
    if row["meta"]:
        try:
            meta = json.loads(row["meta"])
        except Exception:
            meta = {}
    return {
        "name": row["name"],
        "display_name": row["display_name"],
        "system_prompt": row["system_prompt"],
        "allowed_tools": allowed_tools,
        "model": row["model"],
        "jde_overrides": jde_overrides,
        "default_plant": row["default_plant"],
        "route": row["route"],
        "meta": meta,
    }


def get_all() -> List[Dict[str, Any]]:
    init_db()
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM skills ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return [_row_to_skill(r) for r in rows]


def get(name: str) -> Optional[Dict[str, Any]]:
    init_db()
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM skills WHERE name = ?", (name,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return _row_to_skill(row)


def upsert(skill: Dict[str, Any]):
    init_db()
    conn = _connect()
    cur = conn.cursor()
    name = skill.get("name")
    if not name:
        raise ValueError("skill.name required")
    jde_overrides = skill.get("jde_overrides", {}) or {}
    jde_json = json.dumps(jde_overrides)
    jde_blob = _encrypt(jde_json)
    allowed_tools = json.dumps(skill.get("allowed_tools")) if skill.get("allowed_tools") is not None else None
    meta = json.dumps({k: v for k, v in skill.items() if k not in ("name","display_name","system_prompt","allowed_tools","model","jde_overrides","default_plant","route")})
    cur.execute("SELECT 1 FROM skills WHERE name = ?", (name,))
    if cur.fetchone():
        cur.execute(
            "UPDATE skills SET display_name=?, system_prompt=?, allowed_tools=?, model=?, jde_overrides=?, default_plant=?, route=?, meta=? WHERE name=?",
            (
                skill.get("display_name") or name,
                skill.get("system_prompt") or "",
                allowed_tools,
                skill.get("model"),
                jde_blob,
                skill.get("default_plant") or "",
                skill.get("route") or f"/skill/{name}/chat",
                meta,
                name,
            ),
        )
    else:
        cur.execute(
            "INSERT INTO skills (name, display_name, system_prompt, allowed_tools, model, jde_overrides, default_plant, route, meta) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                name,
                skill.get("display_name") or name,
                skill.get("system_prompt") or "",
                allowed_tools,
                skill.get("model"),
                jde_blob,
                skill.get("default_plant") or "",
                skill.get("route") or f"/skill/{name}/chat",
                meta,
            ),
        )
    conn.commit()
    conn.close()


def delete(name: str) -> bool:
    init_db()
    conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM skills WHERE name = ?", (name,))
    ok = cur.rowcount > 0
    conn.commit()
    conn.close()
    return ok
