"""
Fetches articles from configured RSS sources (across all configured
sports) and stores new ones in the DB.
"""

import re
from urllib.parse import urlparse, urlunparse

import feedparser

from config import RSS_SOURCES

# Quick-and-dirty team tagging based on keywords in title/summary.
# Not perfect, but gives you a filterable "teams" column for free.
# One keyword dict per sport -- add a new sport here (matching a new
# top-level key in config.RSS_SOURCES) and the rest of the pipeline
# picks it up automatically.
TEAM_KEYWORDS = {
    "NHL": {
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
    },
    "NFL": {
        "Cardinals": ["cardinals", "arizona"],
        "Falcons": ["falcons", "atlanta"],
        "Ravens": ["ravens", "baltimore"],
        "Bills": ["bills", "buffalo"],
        "Panthers": ["panthers", "carolina"],
        "Bears": ["bears", "chicago"],
        "Bengals": ["bengals", "cincinnati"],
        "Browns": ["browns", "cleveland"],
        "Cowboys": ["cowboys", "dallas"],
        "Broncos": ["broncos", "denver"],
        "Lions": ["lions", "detroit"],
        "Packers": ["packers", "green bay"],
        "Texans": ["texans", "houston"],
        "Colts": ["colts", "indianapolis"],
        "Jaguars": ["jaguars", "jacksonville"],
        "Chiefs": ["chiefs", "kansas city"],
        "Raiders": ["raiders", "las vegas"],
        "Chargers": ["chargers", "los angeles chargers"],
        "Rams": ["rams", "los angeles rams"],
        "Dolphins": ["dolphins", "miami"],
        "Vikings": ["vikings", "minnesota"],
        "Patriots": ["patriots", "new england"],
        "Saints": ["saints", "new orleans"],
        "Giants": ["giants", "new york giants"],
        "Jets": ["jets", "new york jets"],
        "Eagles": ["eagles", "philadelphia"],
        "Steelers": ["steelers", "pittsburgh"],
        "49ers": ["49ers", "san francisco", "niners"],
        "Seahawks": ["seahawks", "seattle"],
        "Buccaneers": ["buccaneers", "tampa bay", "bucs"],
        "Titans": ["titans", "tennessee"],
        "Commanders": ["commanders", "washington"],
    },
}


def tag_teams(text, sport):
    text_lower = text.lower()
    keywords = TEAM_KEYWORDS.get(sport, {})
    matches = [
        team for team, kws in keywords.items()
        if any(kw in text_lower for kw in kws)
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
    """Yields (sport, source_name, feed_url, base_link, entry) for every
    entry across every source in every configured sport.

    feed_url is the URL we fetched the feed from. base_link is the feed's
    channel-level <link> (the real site the feed is about, e.g.
    https://www.nhl.com/news/) -- these differ for proxied feeds.
    """
    for sport, sources in RSS_SOURCES.items():
        for source_name, feed_url in sources.items():
            try:
                feed = feedparser.parse(feed_url)
                if feed.bozo and not feed.entries:
                    print(f"  [warn] {sport} / {source_name}: failed to parse ({feed_url})")
                    continue
                base_link = feed.feed.get("link", feed_url)
                for entry in feed.entries:
                    yield sport, source_name, feed_url, base_link, entry
            except Exception as e:
                print(f"  [warn] {sport} / {source_name}: {e}")


def collect_new_articles(conn, insert_article_fn):
    """
    Fetches all sources across all sports, inserts new articles into the DB.
    Returns the count of newly-inserted articles.
    """
    new_count = 0
    seen_count = 0
    total_sources = sum(len(sources) for sources in RSS_SOURCES.values())

    for sport, source_name, feed_url, base_link, entry in fetch_all_sources():
        seen_count += 1
        url = entry.get("link")
        title = entry.get("title")
        if not url or not title:
            continue

        url = fix_proxy_domain(url, feed_url, base_link)

        published = entry.get("published", entry.get("updated", ""))
        summary = clean_summary(entry.get("summary", ""))
        teams = tag_teams(f"{title} {summary or ''}", sport)

        was_new = insert_article_fn(
            conn, url, title, source_name, published, summary, teams, sport
        )
        if was_new:
            new_count += 1

    print(f"  Checked {seen_count} entries across {total_sources} sources "
          f"({len(RSS_SOURCES)} sports) -> {new_count} new")
    return new_count
