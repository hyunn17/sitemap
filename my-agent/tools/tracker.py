#!/usr/bin/env python3
"""블로그 글 / 체험단 / 리뷰 이력 관리 (SQLite, 표준 라이브러리만 사용).

예시:
  tracker.py post-add --type vs --title "카본매트 vs 온수매트" --file posts/x.html
  tracker.py post-update 1 --status published --url https://...
  tracker.py post-indexed 1 --engine naver
  tracker.py posts --not-indexed
  tracker.py campaign-add --platform stylec --title "..." --review-deadline 2026-12-01
  tracker.py campaign-update 3 --status selected
  tracker.py campaigns --platform reviewtong
  tracker.py review-add --product "..." --rating 5
  tracker.py summary [--days 3]
"""
import argparse
import datetime as dt
import os
import sqlite3
import sys

DB_PATH = os.environ.get(
    "AGENT_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "agent.db")
)

POST_TYPES = ["vs", "top", "review", "tip"]
POST_STATUS = ["draft", "approved", "scheduled", "published"]
CAMPAIGN_STATUS = ["found", "applied", "selected", "rejected", "posted", "done", "cancelled"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY,
  type TEXT NOT NULL,
  title TEXT NOT NULL,
  file TEXT,
  url TEXT,
  status TEXT NOT NULL DEFAULT 'draft',
  scheduled_at TEXT,
  campaign_id INTEGER,
  naver_indexed_at TEXT,
  google_indexed_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS campaigns (
  id INTEGER PRIMARY KEY,
  platform TEXT NOT NULL,
  title TEXT NOT NULL,
  url TEXT,
  reward TEXT,
  apply_deadline TEXT,
  announce_date TEXT,
  review_deadline TEXT,
  status TEXT NOT NULL DEFAULT 'applied',
  post_url TEXT,
  note TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reviews (
  id INTEGER PRIMARY KEY,
  site TEXT NOT NULL DEFAULT 'coupang',
  product TEXT NOT NULL,
  rating INTEGER,
  status TEXT NOT NULL DEFAULT 'posted',
  note TEXT,
  created_at TEXT NOT NULL
);
"""


def now():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def date_arg(s):
    try:
        dt.date.fromisoformat(s)
    except ValueError:
        raise argparse.ArgumentTypeError(f"날짜는 YYYY-MM-DD 형식이어야 해요: {s}")
    return s


def print_rows(rows, cols):
    rows = list(rows)
    if not rows:
        print("(없음)")
        return
    for r in rows:
        print(" | ".join(f"{c}={r[c]}" for c in cols if r[c] not in (None, "")))


def update_row(con, table, row_id, fields):
    fields = {k: v for k, v in fields.items() if v is not None}
    if not fields:
        sys.exit("바꿀 항목이 없어요.")
    if table != "reviews":
        fields["updated_at"] = now()
    sets = ", ".join(f"{k} = ?" for k in fields)
    cur = con.execute(f"UPDATE {table} SET {sets} WHERE id = ?", [*fields.values(), row_id])
    if cur.rowcount == 0:
        sys.exit(f"{table} #{row_id} 를 찾을 수 없어요.")
    con.commit()
    print(f"{table} #{row_id} 업데이트: {', '.join(fields)}")


# ---------- posts ----------
def cmd_post_add(con, a):
    t = now()
    cur = con.execute(
        "INSERT INTO posts (type, title, file, url, status, scheduled_at, campaign_id, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        (a.type, a.title, a.file, a.url, a.status, a.scheduled_at, a.campaign_id, t, t),
    )
    con.commit()
    print(f"post #{cur.lastrowid} 추가")


def cmd_post_update(con, a):
    update_row(con, "posts", a.id, {
        "status": a.status, "url": a.url, "title": a.title,
        "file": a.file, "scheduled_at": a.scheduled_at,
    })


def cmd_post_indexed(con, a):
    update_row(con, "posts", a.id, {f"{a.engine}_indexed_at": now()})


def cmd_posts(con, a):
    q, p = "SELECT * FROM posts WHERE 1=1", []
    if a.status:
        q += " AND status = ?"
        p.append(a.status)
    if a.not_indexed:
        q += " AND status = 'published' AND (naver_indexed_at IS NULL OR google_indexed_at IS NULL)"
    q += " ORDER BY id DESC LIMIT ?"
    p.append(a.limit)
    print_rows(con.execute(q, p), ["id", "type", "status", "title", "url", "scheduled_at",
                                   "naver_indexed_at", "google_indexed_at"])


# ---------- campaigns ----------
def cmd_campaign_add(con, a):
    if a.url:
        dup = con.execute("SELECT id FROM campaigns WHERE url = ?", (a.url,)).fetchone()
        if dup:
            sys.exit(f"이미 기록된 캠페인이에요: #{dup['id']}")
    t = now()
    cur = con.execute(
        "INSERT INTO campaigns (platform, title, url, reward, apply_deadline, announce_date,"
        " review_deadline, status, note, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (a.platform, a.title, a.url, a.reward, a.apply_deadline, a.announce_date,
         a.review_deadline, a.status, a.note, t, t),
    )
    con.commit()
    print(f"campaign #{cur.lastrowid} 추가")


def cmd_campaign_update(con, a):
    update_row(con, "campaigns", a.id, {
        "status": a.status, "post_url": a.post_url, "review_deadline": a.review_deadline,
        "announce_date": a.announce_date, "note": a.note,
    })


def cmd_campaigns(con, a):
    q, p = "SELECT * FROM campaigns WHERE 1=1", []
    if a.platform:
        q += " AND platform = ?"
        p.append(a.platform)
    if a.status:
        q += " AND status = ?"
        p.append(a.status)
    q += " ORDER BY id DESC LIMIT ?"
    p.append(a.limit)
    print_rows(con.execute(q, p), ["id", "platform", "status", "title", "reward", "apply_deadline",
                                   "announce_date", "review_deadline", "url", "post_url"])


# ---------- reviews ----------
def cmd_review_add(con, a):
    cur = con.execute(
        "INSERT INTO reviews (site, product, rating, status, note, created_at) VALUES (?,?,?,?,?,?)",
        (a.site, a.product, a.rating, a.status, a.note, now()),
    )
    con.commit()
    print(f"review #{cur.lastrowid} 추가")


def cmd_reviews(con, a):
    print_rows(con.execute("SELECT * FROM reviews ORDER BY id DESC LIMIT ?", (a.limit,)),
               ["id", "site", "product", "rating", "status", "created_at"])


# ---------- summary ----------
def build_summary(con, days):
    today = dt.date.today()
    until = (today + dt.timedelta(days=days)).isoformat()
    t = today.isoformat()
    lines = [f"📋 {t} 현황"]

    def section(title, rows, fmt):
        rows = list(rows)
        if rows:
            lines.append(f"\n{title}")
            lines.extend("• " + fmt(r) for r in rows)

    section("🚨 리뷰 마감 지남", con.execute(
        "SELECT * FROM campaigns WHERE status = 'selected' AND review_deadline < ? ORDER BY review_deadline",
        (t,)), lambda r: f"#{r['id']} {r['title']} (마감 {r['review_deadline']})")
    section(f"⏰ {days}일 안에 리뷰 마감", con.execute(
        "SELECT * FROM campaigns WHERE status = 'selected' AND review_deadline BETWEEN ? AND ?"
        " ORDER BY review_deadline", (t, until)),
        lambda r: f"#{r['id']} {r['title']} (마감 {r['review_deadline']})")
    section("✍️ 선정됐지만 글 미작성", con.execute(
        "SELECT c.* FROM campaigns c WHERE c.status = 'selected'"
        " AND NOT EXISTS (SELECT 1 FROM posts p WHERE p.campaign_id = c.id)"),
        lambda r: f"#{r['id']} {r['title']}")
    section(f"📢 {days}일 안에 발표", con.execute(
        "SELECT * FROM campaigns WHERE status = 'applied' AND announce_date BETWEEN ? AND ?"
        " ORDER BY announce_date", (t, until)),
        lambda r: f"#{r['id']} [{r['platform']}] {r['title']} (발표 {r['announce_date']})")
    section("🕒 예약 발행 대기", con.execute(
        "SELECT * FROM posts WHERE status = 'scheduled' ORDER BY scheduled_at"),
        lambda r: f"#{r['id']} {r['title']} ({r['scheduled_at']})")
    section("🔍 색인 요청 안 한 글", con.execute(
        "SELECT * FROM posts WHERE status = 'published'"
        " AND (naver_indexed_at IS NULL OR google_indexed_at IS NULL)"),
        lambda r: f"#{r['id']} {r['title']} (네이버 {'✅' if r['naver_indexed_at'] else '❌'}"
                  f" / 구글 {'✅' if r['google_indexed_at'] else '❌'})")
    section("📝 초안", con.execute("SELECT * FROM posts WHERE status IN ('draft','approved')"),
            lambda r: f"#{r['id']} [{r['type']}] {r['title']}")

    if len(lines) == 1:
        lines.append("\n남은 일이 없어요 🎉")
    return "\n".join(lines)


def cmd_summary(con, a):
    print(build_summary(con, a.days))


def main(argv=None):
    ap = argparse.ArgumentParser(description="블로그·체험단·리뷰 이력 관리")
    sp = ap.add_subparsers(dest="cmd", required=True)

    p = sp.add_parser("post-add", help="블로그 글 추가")
    p.add_argument("--type", required=True, choices=POST_TYPES)
    p.add_argument("--title", required=True)
    p.add_argument("--file")
    p.add_argument("--url")
    p.add_argument("--status", default="draft", choices=POST_STATUS)
    p.add_argument("--scheduled-at")
    p.add_argument("--campaign-id", type=int, help="체험단 글이면 캠페인 ID")
    p.set_defaults(fn=cmd_post_add)

    p = sp.add_parser("post-update", help="글 상태/URL 변경")
    p.add_argument("id", type=int)
    p.add_argument("--status", choices=POST_STATUS)
    p.add_argument("--url")
    p.add_argument("--title")
    p.add_argument("--file")
    p.add_argument("--scheduled-at")
    p.set_defaults(fn=cmd_post_update)

    p = sp.add_parser("post-indexed", help="색인 요청 완료 기록")
    p.add_argument("id", type=int)
    p.add_argument("--engine", required=True, choices=["naver", "google"])
    p.set_defaults(fn=cmd_post_indexed)

    p = sp.add_parser("posts", help="글 목록")
    p.add_argument("--status", choices=POST_STATUS)
    p.add_argument("--not-indexed", action="store_true")
    p.add_argument("--limit", type=int, default=30)
    p.set_defaults(fn=cmd_posts)

    p = sp.add_parser("campaign-add", help="체험단 캠페인 추가")
    p.add_argument("--platform", required=True, help="stylec, reviewtong 등")
    p.add_argument("--title", required=True)
    p.add_argument("--url")
    p.add_argument("--reward")
    p.add_argument("--apply-deadline", type=date_arg)
    p.add_argument("--announce-date", type=date_arg)
    p.add_argument("--review-deadline", type=date_arg)
    p.add_argument("--status", default="applied", choices=CAMPAIGN_STATUS)
    p.add_argument("--note")
    p.set_defaults(fn=cmd_campaign_add)

    p = sp.add_parser("campaign-update", help="캠페인 상태 변경")
    p.add_argument("id", type=int)
    p.add_argument("--status", choices=CAMPAIGN_STATUS)
    p.add_argument("--post-url")
    p.add_argument("--review-deadline", type=date_arg)
    p.add_argument("--announce-date", type=date_arg)
    p.add_argument("--note")
    p.set_defaults(fn=cmd_campaign_update)

    p = sp.add_parser("campaigns", help="캠페인 목록")
    p.add_argument("--platform")
    p.add_argument("--status", choices=CAMPAIGN_STATUS)
    p.add_argument("--limit", type=int, default=30)
    p.set_defaults(fn=cmd_campaigns)

    p = sp.add_parser("review-add", help="리뷰 작성 기록")
    p.add_argument("--product", required=True)
    p.add_argument("--site", default="coupang")
    p.add_argument("--rating", type=int, choices=range(1, 6))
    p.add_argument("--status", default="posted", choices=["draft", "posted"])
    p.add_argument("--note")
    p.set_defaults(fn=cmd_review_add)

    p = sp.add_parser("reviews", help="리뷰 목록")
    p.add_argument("--limit", type=int, default=30)
    p.set_defaults(fn=cmd_reviews)

    p = sp.add_parser("summary", help="오늘 할 일 요약")
    p.add_argument("--days", type=int, default=3)
    p.set_defaults(fn=cmd_summary)

    a = ap.parse_args(argv)
    con = connect()
    try:
        a.fn(con, a)
    finally:
        con.close()


if __name__ == "__main__":
    main()
