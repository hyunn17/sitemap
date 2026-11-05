"""SQLite 저장소: 영상, 분석, 후킹 멘트, 템플릿, 제품 리서치, 대본."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    video_id TEXT PRIMARY KEY,
    title TEXT, channel_id TEXT, channel_title TEXT, description TEXT,
    published_at TEXT, duration_sec INTEGER,
    views INTEGER, likes INTEGER, comments INTEGER, subscribers INTEGER,
    viral_score REAL, views_per_hour REAL,
    keyword TEXT, transcript TEXT, transcript_source TEXT,
    fetched_at TEXT
);
CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT UNIQUE, data TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS hooks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT UNIQUE, hook_type TEXT, pattern TEXT, why_it_works TEXT,
    language TEXT, video_id TEXT, views INTEGER, viral_score REAL,
    favorite INTEGER DEFAULT 0, created_at TEXT
);
CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE, data TEXT, source TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS research (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product TEXT, raw TEXT, report TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS scripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product TEXT, research_id INTEGER, template_id INTEGER, data TEXT, created_at TEXT
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init() -> None:
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with conn() as c:
        c.executescript(SCHEMA)


@contextmanager
def conn():
    c = sqlite3.connect(config.DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def rows(sql: str, params=()) -> list[dict]:
    with conn() as c:
        return [dict(r) for r in c.execute(sql, params).fetchall()]


def one(sql: str, params=()) -> dict | None:
    r = rows(sql, params)
    return r[0] if r else None


def execute(sql: str, params=()) -> int:
    with conn() as c:
        cur = c.execute(sql, params)
        return cur.lastrowid


# ---- videos -----------------------------------------------------------------

VIDEO_COLS = [
    "video_id", "title", "channel_id", "channel_title", "description", "published_at",
    "duration_sec", "views", "likes", "comments", "subscribers", "viral_score",
    "views_per_hour", "keyword",
]


def upsert_video(v: dict) -> None:
    cols = VIDEO_COLS + ["fetched_at"]
    vals = [v.get(k) for k in VIDEO_COLS] + [now()]
    updates = ", ".join(f"{k}=excluded.{k}" for k in cols if k != "video_id")
    execute(
        f"INSERT INTO videos ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))}) "
        f"ON CONFLICT(video_id) DO UPDATE SET {updates}",
        vals,
    )


def set_transcript(video_id: str, text: str, source: str) -> None:
    execute(
        "UPDATE videos SET transcript=?, transcript_source=? WHERE video_id=?",
        (text, source, video_id),
    )


def get_video(video_id: str) -> dict | None:
    return one("SELECT * FROM videos WHERE video_id=?", (video_id,))


def list_videos(limit: int = 100) -> list[dict]:
    return rows(
        "SELECT v.*, (a.id IS NOT NULL) AS analyzed FROM videos v "
        "LEFT JOIN analyses a ON a.video_id=v.video_id "
        "ORDER BY v.viral_score DESC LIMIT ?",
        (limit,),
    )


# ---- analyses & hooks ---------------------------------------------------------

def save_analysis(video_id: str, data: dict) -> None:
    execute(
        "INSERT INTO analyses (video_id, data, created_at) VALUES (?,?,?) "
        "ON CONFLICT(video_id) DO UPDATE SET data=excluded.data, created_at=excluded.created_at",
        (video_id, json.dumps(data, ensure_ascii=False), now()),
    )


def get_analysis(video_id: str) -> dict | None:
    r = one("SELECT data FROM analyses WHERE video_id=?", (video_id,))
    return json.loads(r["data"]) if r else None


def list_analyses(limit: int = 30) -> list[dict]:
    out = []
    for r in rows(
        "SELECT a.video_id, a.data, v.title, v.views, v.viral_score FROM analyses a "
        "JOIN videos v ON v.video_id=a.video_id ORDER BY v.viral_score DESC LIMIT ?",
        (limit,),
    ):
        d = json.loads(r["data"])
        d.update(video_id=r["video_id"], title=r["title"], views=r["views"],
                 viral_score=r["viral_score"])
        out.append(d)
    return out


def add_hook(h: dict) -> bool:
    """중복(같은 문장)은 무시. 새로 추가되면 True."""
    with conn() as c:
        cur = c.execute(
            "INSERT OR IGNORE INTO hooks (text, hook_type, pattern, why_it_works, language, "
            "video_id, views, viral_score, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (h["text"].strip(), h.get("hook_type"), h.get("pattern"), h.get("why_it_works"),
             h.get("language"), h.get("video_id"), h.get("views"), h.get("viral_score"), now()),
        )
        return cur.rowcount > 0


def list_hooks(hook_type: str | None = None, q: str | None = None, limit: int = 200) -> list[dict]:
    sql, params = "SELECT * FROM hooks WHERE 1=1", []
    if hook_type:
        sql += " AND hook_type=?"
        params.append(hook_type)
    if q:
        sql += " AND (text LIKE ? OR pattern LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    sql += " ORDER BY favorite DESC, viral_score DESC LIMIT ?"
    params.append(limit)
    return rows(sql, params)


def hook_types() -> list[dict]:
    return rows("SELECT hook_type, COUNT(*) AS n FROM hooks GROUP BY hook_type ORDER BY n DESC")


def toggle_favorite(hook_id: int) -> None:
    execute("UPDATE hooks SET favorite = 1 - favorite WHERE id=?", (hook_id,))


def delete_hook(hook_id: int) -> None:
    execute("DELETE FROM hooks WHERE id=?", (hook_id,))


# ---- templates ------------------------------------------------------------------

def save_template(t: dict, source: str) -> int:
    execute(
        "INSERT INTO templates (name, data, source, created_at) VALUES (?,?,?,?) "
        "ON CONFLICT(name) DO UPDATE SET data=excluded.data, source=excluded.source, "
        "created_at=excluded.created_at",
        (t["name"], json.dumps(t, ensure_ascii=False), source, now()),
    )
    return one("SELECT id FROM templates WHERE name=?", (t["name"],))["id"]


def list_templates() -> list[dict]:
    out = []
    for r in rows("SELECT * FROM templates ORDER BY id"):
        d = json.loads(r["data"])
        d.update(id=r["id"], source=r["source"], created_at=r["created_at"])
        out.append(d)
    return out


def delete_template(tid: int) -> None:
    execute("DELETE FROM templates WHERE id=?", (tid,))


# ---- research & scripts ------------------------------------------------------------

def save_research(product: str, raw: dict, report: dict) -> int:
    return execute(
        "INSERT INTO research (product, raw, report, created_at) VALUES (?,?,?,?)",
        (product, json.dumps(raw, ensure_ascii=False), json.dumps(report, ensure_ascii=False), now()),
    )


def get_research(rid: int) -> dict | None:
    r = one("SELECT * FROM research WHERE id=?", (rid,))
    if not r:
        return None
    r["raw"] = json.loads(r["raw"])
    r["report"] = json.loads(r["report"])
    return r


def list_research() -> list[dict]:
    return rows("SELECT id, product, created_at FROM research ORDER BY id DESC LIMIT 50")


def save_script(product: str, research_id: int | None, template_id: int | None, data: dict) -> int:
    return execute(
        "INSERT INTO scripts (product, research_id, template_id, data, created_at) VALUES (?,?,?,?,?)",
        (product, research_id, template_id, json.dumps(data, ensure_ascii=False), now()),
    )


def list_scripts() -> list[dict]:
    out = []
    for r in rows("SELECT * FROM scripts ORDER BY id DESC LIMIT 50"):
        r["data"] = json.loads(r["data"])
        out.append(r)
    return out
