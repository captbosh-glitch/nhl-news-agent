"""
Fetches articles from configured RSS sources and stores new ones in the DB.
"""

import re
from urllib.parse import urlparse, urlunparse

import feedparser

from config import RSS_SOURCES

# Quick-and-dirty team tagging based on keywords in title/summary.
# Not perfect, but gives you a filterable "teams" column for free.
TEAM_KEYWORDS = {
    "Bruins": ["bruins", "boston"],
    "Sabres": ["sabres", "buffalo"],
    "Red Wings": ["red wings", "detroit"],
    "Panthers": ["panthers", "florida"],
    "Canadiens": ["canadiens", "montreal", "habs"],
    "Senators": ["senators", "ottawa"],
    "Lightning": ["lightning", "tampa"],
    "Maple Leafs": ["maple leafs", "leafs", "toronto"],
    "Hurricanes": ["hurricanes", "carolina"],
    "Blue Jackets": ["blue jackets", "columbus"],
    "Devils": ["devils", "new jersey"],
    "Islanders": ["islanders"],
    "Rangers": ["rangers", "new york rangers"],
    "Flyers": ["flyers", "philadelphia"],
    "Penguins": ["penguins", "pittsburgh"],
    "Capitals": ["capitals", "washington"],
    "Blackhawks": ["blackhawks", "chicago"],
    "Avalanche": ["avalanche", "colorado"],
    "Stars": ["stars", "dallas"],
    "Wild": ["wild", "minnesota"],
    "Predators": ["predators", "nashville"],
    "Blues": ["blues", "st. louis", "st louis"],
    "Jets": ["jets", "winnipeg"],
    "Coyotes": ["coyotes", "arizona", "utah hockey"],
    "Ducks": ["ducks", "anaheim"],
    "Flames": ["flames", "calgary"],
    "Oilers": ["oilers", "edmonton"],
    "Kings": ["kings", "los angeles"],
    "Sharks": ["sharks", "san jose"],
    "Kraken": ["kraken", "seattle"],
    "Canucks": ["canucks", "vancouver"],
    "Golden Knights": ["golden knights", "vegas"],
}


def tag_teams(text):
    text_lower = text.lower()
    matches = [
        team for team, keywords in TEAM_KEYWORDS.items()
        if any(kw in text_lower for kw in keywords)
    ]
    return ", ".join(matches) if matches else None


def clean_summary(raw_summary):
    """Strip HTML tags from RSS summary fields."""
    if not raw_summary:
        return None
    return re.sub(r"<[^>]+>", "", raw_summary).strip()


def fix_proxy_domain(url, feed_url, base_link):
    """
    feedparser ALWAYS resolves relative entry links (like "/news/foo")
    against the URL the feed was fetched from -- this is mandated by the
    XML:Base spec and cannot be disabled via any parse() option.

    For a proxied feed (like the NHL.com one, which is hosted on a
    different domain than the articles it lists), that produces a link on
    the *proxy's* domain instead of the real article's domain. This
    detects that case and rewrites the domain to match the feed's real
    channel link instead, leaving normal (non-proxied) feeds untouched.
    """
    fetched_domain = urlparse(feed_url).netloc
    real_domain = urlparse(base_link).netloc
    url_domain = urlparse(url).netloc

    if url_domain == fetched_domain and fetched_domain != real_domain:
        parts = urlparse(url)
        return urlunparse(parts._replace(netloc=real_domain))
    return url


def fetch_all_sources():
    """Yields (source_name, feed_url, base_link, entry) for every entry
    across all configured feeds.

    feed_url is the URL we fetched the feed from. base_link is the feed's
    channel-level <link> (the real site the feed is about, e.g.
    https://www.nhl.com/news/) -- these differ for proxied feeds.
    """
    for source_name, feed_url in RSS_SOURCES.items():
        try:
            feed = feedparser.parse(feed_url)
            if feed.bozo and not feed.entries:
                print(f"  [warn] {source_name}: failed to parse ({feed_url})")
                continue
            base_link = feed.feed.get("link", feed_url)
            for entry in feed.entries:
                yield source_name, feed_url, base_link, entry
        except Exception as e:
            print(f"  [warn] {source_name}: {e}")


def collect_new_articles(conn, insert_article_fn):
    """
    Fetches all sources, inserts new articles into the DB.
    Returns the count of newly-inserted articles.
    """
    new_count = 0
    seen_count = 0

    for source_name, feed_url, base_link, entry in fetch_all_sources():
        seen_count += 1
        url = entry.get("link")
        title = entry.get("title")
        if not url or not title:
            continue

        url = fix_proxy_domain(url, feed_url, base_link)

        published = entry.get("published", entry.get("updated", ""))
        summary = clean_summary(entry.get("summary", ""))
        teams = tag_teams(f"{title} {summary or ''}")

        was_new = insert_article_fn(conn, url, title, source_name, published, summary, teams)
        if was_new:
            new_count += 1

    print(f"  Checked {seen_count} entries across {len(RSS_SOURCES)} sources -> {new_count} new")
    return new_count