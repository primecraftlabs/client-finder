import json
import sqlite3
from datetime import date

from . import config

STATUSES = ["new", "drafted", "sent", "replied", "won", "lost", "skipped"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY,
    place_id TEXT UNIQUE,
    name TEXT,
    category TEXT,
    city TEXT,
    address TEXT,
    phone TEXT,
    intl_phone TEXT,
    website TEXT,
    rating REAL,
    reviews INTEGER,
    maps_url TEXT,
    site_status TEXT,
    site_issues TEXT,
    site_title TEXT,
    score INTEGER DEFAULT 0,
    pitch_angle TEXT,
    draft TEXT,
    status TEXT DEFAULT 'new',
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(id),
    direction TEXT CHECK (direction IN ('out', 'in')),
    text TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def insert_lead(conn, lead: dict) -> bool:
    """Insert a lead; returns False if we already have this business."""
    cur = conn.execute(
        """INSERT OR IGNORE INTO leads
           (place_id, name, category, city, address, phone, intl_phone, website, rating, reviews, maps_url)
           VALUES (:place_id, :name, :category, :city, :address, :phone, :intl_phone, :website,
                   :rating, :reviews, :maps_url)""",
        lead,
    )
    conn.commit()
    return cur.rowcount == 1


def update_lead(conn, lead_id: int, **fields):
    if "site_issues" in fields and not isinstance(fields["site_issues"], str):
        fields["site_issues"] = json.dumps(fields["site_issues"])
    sets = ", ".join(f"{k} = :{k}" for k in fields)
    conn.execute(
        f"UPDATE leads SET {sets}, updated_at = CURRENT_TIMESTAMP WHERE id = :id",
        {**fields, "id": lead_id},
    )
    conn.commit()


def get_lead(conn, lead_id: int) -> dict:
    return _to_dict(conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone())


def list_leads(conn, status: str | None = None, min_score: int = 0, where: str = "") -> list[dict]:
    sql = "SELECT * FROM leads WHERE score >= ?"
    params: list = [min_score]
    if status:
        sql += " AND status = ?"
        params.append(status)
    if where:
        sql += f" AND {where}"
    sql += " ORDER BY score DESC, reviews DESC"
    return [_to_dict(r) for r in conn.execute(sql, params).fetchall()]


def add_message(conn, lead_id: int, direction: str, text: str):
    conn.execute(
        "INSERT INTO messages (lead_id, direction, text) VALUES (?, ?, ?)",
        (lead_id, direction, text),
    )
    conn.commit()


def get_messages(conn, lead_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM messages WHERE lead_id = ? ORDER BY id", (lead_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def sent_today(conn) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM messages WHERE direction = 'out' AND date(created_at, 'localtime') = ?",
        (date.today().isoformat(),),
    ).fetchone()
    return row[0]


def counts(conn) -> dict:
    rows = conn.execute("SELECT status, COUNT(*) FROM leads GROUP BY status").fetchall()
    return {status: n for status, n in rows}


def _to_dict(row) -> dict:
    if row is None:
        return {}
    d = dict(row)
    d["site_issues"] = json.loads(d["site_issues"]) if d.get("site_issues") else []
    return d
