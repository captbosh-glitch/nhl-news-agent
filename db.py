"""
SQLite storage layer for collected sports news.

Two tables:
  - articles: every article we've collected, deduped by URL, tagged by sport
  - daily_digests: one curated summary per day, across all sports (optional,
    needs Claude API)
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
    sport TEXT NOT NULL DEFAULT 'NHL',
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


def _migrate(conn):
    """
    Handles upgrading a database created before the multi-sport update.
    CREATE TABLE IF NOT EXISTS won't add new columns to an already-existing
    table, so an explicit ALTER TABLE is needed for anyone with an existing
    nhl_news.db from before this change. New/empty databases already get
    the 'sport' column from SCHEMA above, so this is a no-op for those.
    """
    existing_columns = {row["name"] for row in conn.execute("PRAGMA table_info(articles)")}
    if "sport" not in existing_columns:
        # DEFAULT 'NHL' backfills every pre-existing row correctly, since
        # this project only collected NHL news before this update.
        conn.execute("ALTER TABLE articles ADD COLUMN sport TEXT NOT NULL DEFAULT 'NHL'")


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)


def insert_article(conn, url, title, source, published, summary=None, teams=None, sport="NHL"):
    """Insert an article. Returns True if it was new, False if it was a duplicate."""
    try:
        conn.execute(
            """INSERT INTO articles (url, title, source, published, summary, teams, sport)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (url, title, source, published, summary, teams, sport),
        )
        return True
    except sqlite3.IntegrityError:
        # URL already exists -- not new
        return False


def get_articles_since(conn, since_iso_date, sport=None):
    """If sport is given, only returns articles for that sport; otherwise
    returns articles across all sports (used for the combined digest)."""
    if sport:
        cur = conn.execute(
            "SELECT * FROM articles WHERE collected_at >= ? AND sport = ? "
            "ORDER BY collected_at DESC",
            (since_iso_date, sport),
        )
    else:
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
