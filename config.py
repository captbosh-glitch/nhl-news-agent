"""
Configuration for the NHL news collector.
Add/remove RSS feed URLs here as you find more/better sources.
"""

RSS_SOURCES = {
    # NHL.com stopped publishing a native RSS feed some time ago. This is a
    # well-known open-source proxy that regenerates one live from nhl.com/news
    # (see https://github.com/clokep/nhl-news-rss). Verified working.
    "NHL.com": "https://www.to-rss.xyz/nhl/news/",
    "ESPN NHL": "https://www.espn.com/espn/rss/nhl/news",
    "Sportsnet NHL": "https://www.sportsnet.ca/hockey/nhl/feed/",
    "Yahoo Sports NHL": "https://sports.yahoo.com/nhl/rss.xml",
    # TSN's public RSS feed appears to be discontinued as of writing --
    # dropped for now. Add a replacement here if you find a working one.
}

DB_PATH = "nhl_news.db"

# Set this in your environment (export ANTHROPIC_API_KEY=...) to enable
# the optional daily digest / curation step. If unset, the collector
# still runs fine -- it just skips curation.
ANTHROPIC_MODEL = "claude-sonnet-4-6"
