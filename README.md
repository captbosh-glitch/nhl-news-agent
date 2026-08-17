# NHL News Agent

Collects NHL news daily from a handful of RSS feeds, dedupes it, tags articles
by team, stores everything in SQLite, and (optionally, if you set an Anthropic
API key) generates a short curated digest of the day's news using Claude.

## Setup

```bash
cd nhl_news_agent
pip install -r requirements.txt
```

Optional, to enable the curated digest step:

```bash
export ANTHROPIC_API_KEY=your-key-here
```

## Run it

```bash
python main.py
```

First run creates `nhl_news.db` (SQLite) in this folder with two tables:

- **articles** — every article collected, deduped by URL. Columns: `id, url,
  title, source, published, summary, teams, collected_at`
- **daily_digests** — one curated summary per day (only populated if the
  Anthropic API key is set). Columns: `id, digest_date, digest_text,
  article_count, created_at`

You can inspect it with any SQLite browser, or from the command line:

```bash
sqlite3 nhl_news.db "SELECT title, source, teams FROM articles ORDER BY collected_at DESC LIMIT 10;"
```

## Scheduling it to run daily

**Option A — cron (Mac/Linux, if this runs on a machine that's always on):**

```bash
crontab -e
```

Add a line to run it every day at 7am:

```
0 7 * * * cd /full/path/to/nhl_news_agent && /usr/bin/python3 main.py >> run.log 2>&1
```

**Option B — GitHub Actions (free, no server needed, but the SQLite file
won't persist between runs unless you commit it back to the repo or switch
to a hosted database):**

Create `.github/workflows/daily.yml`:

```yaml
name: Daily NHL News Collection
on:
  schedule:
    - cron: '0 12 * * *'  # 12:00 UTC daily -- adjust for your timezone
  workflow_dispatch: {}    # lets you trigger it manually too

jobs:
  collect:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python main.py
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      - name: Commit updated database
        run: |
          git config user.name "nhl-news-bot"
          git config user.email "bot@example.com"
          git add nhl_news.db
          git commit -m "Daily NHL news update" || echo "Nothing to commit"
          git push
```

If you go this route, you'll want to `git add nhl_news.db` once manually
first so it's tracked.

## Viewing the data: static HTML dashboard

Run this any time you want a refreshed local page to browse what's been
collected:

```bash
python generate_page.py
```

This reads `nhl_news.db` and writes `dashboard.html` in the same folder.
Double-click it (or `open dashboard.html` / drag into a browser tab) --
no server needed. It shows the latest curated digest at the top, and every
collected article below with click-to-filter team chips.

`preview_dashboard.html` in this project is a one-time preview built from
sample data, just so you can see what it looks like before you've collected
anything real -- delete it whenever, it's not used by the app.

If you want the dashboard to always be current, add a line to the end of
`main.py`'s `main()` function:

```python
import generate_page
generate_page.generate()
```

Then it regenerates automatically every time the daily collection runs.

## Extending it

- **More/better sources**: edit `RSS_SOURCES` in `config.py`. Team-specific
  sites (e.g. individual NHL.com team pages) often have their own RSS feeds
  too.
- **Better team tagging**: `TEAM_KEYWORDS` in `collector.py` is a simple
  keyword match. You could swap this for a Claude API call if you want more
  accurate multi-team / player-based tagging.
- **Migrating to Postgres later**: the `db.py` module is intentionally small
  and isolated -- when you're ready, swap `sqlite3` calls for
  `psycopg2`/`asyncpg` calls and the schema translates almost 1:1.
- **Serving the data**: once this is running for a few days, a simple
  Flask/FastAPI endpoint reading from `articles`/`daily_digests` gets you a
  basic API or webpage without much extra work.
