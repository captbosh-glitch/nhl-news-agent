"""
Configuration for the multi-sport news collector.
Add/remove RSS feed URLs per sport here as you find more/better sources.
"""

# Each sport has its own set of RSS sources. Add a new sport by adding a
# new top-level key here (plus a matching TEAM_KEYWORDS block in
# collector.py) -- everything else (db, digest, dashboard tabs) picks it
# up automatically.
RSS_SOURCES = {
    "NHL": {
        # NHL.com stopped publishing a native RSS feed some time ago. This
        # is a well-known open-source proxy that regenerates one live from
        # nhl.com/news (see https://github.com/clokep/nhl-news-rss).
        "NHL.com": "https://www.to-rss.xyz/nhl/news/",
        "ESPN NHL": "https://www.espn.com/espn/rss/nhl/news",
        "Sportsnet NHL": "https://www.sportsnet.ca/hockey/nhl/feed/",
        "Yahoo Sports NHL": "https://sports.yahoo.com/nhl/rss.xml",
        # TSN's public RSS feed appears to be discontinued -- dropped.
    },
    "NFL": {
        # Both verified working directly.
        "ESPN NFL": "https://www.espn.com/espn/rss/nfl/news",
        "Yahoo Sports NFL": "https://sports.yahoo.com/nfl/rss.xml",
    },
    "MLB": {
        # Both verified working directly (CBS Sports especially -- pulled
        # real same-day articles when tested).
        "ESPN MLB": "https://www.espn.com/espn/rss/mlb/news",
        "CBS Sports MLB": "https://www.cbssports.com/rss/headlines/mlb",
    },
    "NBA": {
        # Both verified working directly.
        "ESPN NBA": "https://www.espn.com/espn/rss/nba/news",
        "CBS Sports NBA": "https://www.cbssports.com/rss/headlines/nba/",
    },
}

DB_PATH = "nhl_news.db"  # kept as-is (not renamed) so existing collected data isn't orphaned

# Set this in your environment (export ANTHROPIC_API_KEY=...) to enable
# the optional daily digest / curation step. If unset, the collector
# still runs fine -- it just skips curation.
ANTHROPIC_MODEL = "claude-sonnet-4-6"
