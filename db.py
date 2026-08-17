"""
SQLite storage layer for collected NHL news.

Two tables:
  - articles: every article we've collected, deduped by URL
  - daily_digests: one curated summary per day (optional, needs Claude API)
"""

import sqlite3
from contextlib import contextmanager

from config import DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    published TEXT,
    summary TEXT,
    teams TEXT,
    collected_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS daily_digests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    digest_date TEXT UNIQUE NOT NULL,
    digest_text TEXT NOT NULL,
    article_count INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def insert_article(conn, url, title, source, published, summary=None, teams=None):
    """Insert an article. Returns True if it was new, False if it was a duplicate."""
    try:
        conn.execute(
            """INSERT INTO articles (url, title, source, published, summary, teams)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (url, title, source, published, summary, teams),
        )
        return True
    except sqlite3.IntegrityError:
        # URL already exists -- not new
        return False


def get_articles_since(conn, since_iso_date):
    cur = conn.execute(
        "SELECT * FROM articles WHERE collected_at >= ? ORDER BY collected_at DESC",
        (since_iso_date,),
    )
    return cur.fetchall()


def save_digest(conn, digest_date, digest_text, article_count):
    conn.execute(
        """INSERT INTO daily_digests (digest_date, digest_text, article_count)
           VALUES (?, ?, ?)
           ON CONFLICT(digest_date) DO UPDATE SET
             digest_text=excluded.digest_text,
             article_count=excluded.article_count""",
        (digest_date, digest_text, article_count),
    )
