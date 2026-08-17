"""
Generates a static HTML dashboard (dashboard.html) from the collected
NHL news data. Run this any time after main.py to refresh the page --
or call generate() from main.py to regenerate it automatically after
every collection run.

Usage:
    python generate_page.py
"""

import json
from datetime import datetime

import db


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NHL News Desk</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Teko:wght@500;600;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #0A0E13;
    --panel: #121920;
    --panel-hover: #182029;
    --border: #232D38;
    --ice: #4FC3F7;
    --goal: #D62828;
    --text: #E8EDF2;
    --text-dim: #7C8B9B;
  }}

  * {{ box-sizing: border-box; }}

  body {{
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: 'Inter', sans-serif;
    -webkit-font-smoothing: antialiased;
  }}

  .wrap {{
    max-width: 780px;
    margin: 0 auto;
    padding: 0 20px 80px;
  }}

  /* --- Scoreboard header (signature element) --- */
  .scoreboard {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 14px 20px;
    margin: 0 -20px 0;
    background: linear-gradient(180deg, #0D131A 0%, #0A0E13 100%);
    border-bottom: 2px solid var(--border);
    position: sticky;
    top: 0;
    z-index: 10;
  }}

  .scoreboard-left {{
    display: flex;
    align-items: center;
    gap: 10px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    letter-spacing: 0.06em;
    color: var(--text-dim);
    text-transform: uppercase;
  }}

  .goal-light {{
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: var(--goal);
    box-shadow: 0 0 8px 2px rgba(214, 40, 40, 0.7);
    animation: pulse 1.8s ease-in-out infinite;
    flex-shrink: 0;
  }}

  @keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.35; }}
  }}

  @media (prefers-reduced-motion: reduce) {{
    .goal-light {{ animation: none; }}
  }}

  .scoreboard-clock {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    color: var(--ice);
    letter-spacing: 0.04em;
  }}

  /* --- Digest hero --- */
  .digest {{
    margin-top: 28px;
    padding: 24px 24px 26px;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
  }}

  .digest-eyebrow {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.12em;
    color: var(--ice);
    text-transform: uppercase;
    margin-bottom: 6px;
  }}

  .digest h1 {{
    font-family: 'Teko', sans-serif;
    font-weight: 600;
    font-size: 40px;
    letter-spacing: 0.01em;
    margin: 0 0 12px;
    line-height: 0.95;
    text-transform: uppercase;
  }}

  .digest p {{
    font-size: 15.5px;
    line-height: 1.65;
    color: var(--text);
    margin: 0 0 14px;
    white-space: pre-line;
  }}

  .digest-meta {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: var(--text-dim);
  }}

  .no-digest {{
    font-size: 14px;
    color: var(--text-dim);
    line-height: 1.6;
  }}

  /* --- Filter chips --- */
  .filters {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 24px 0 20px;
  }}

  .chip {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    letter-spacing: 0.03em;
    padding: 7px 13px;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: transparent;
    color: var(--text-dim);
    cursor: pointer;
    transition: all 0.15s ease;
    text-transform: uppercase;
  }}

  .chip:hover {{
    border-color: var(--ice);
    color: var(--text);
  }}

  .chip.active {{
    background: var(--ice);
    border-color: var(--ice);
    color: #0A0E13;
    font-weight: 700;
  }}

  /* --- Article list --- */
  .section-label {{
    font-family: 'Teko', sans-serif;
    font-size: 22px;
    font-weight: 600;
    letter-spacing: 0.02em;
    text-transform: uppercase;
    color: var(--text-dim);
    margin: 8px 0 12px;
  }}

  .article {{
    display: block;
    padding: 16px 18px;
    margin-bottom: 10px;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    text-decoration: none;
    color: var(--text);
    transition: background 0.15s ease, border-color 0.15s ease;
  }}

  .article:hover {{
    background: var(--panel-hover);
    border-color: var(--ice);
  }}

  .article-top {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }}

  .article-title {{
    font-size: 15.5px;
    font-weight: 600;
    line-height: 1.4;
    margin-bottom: 4px;
  }}

  .article-summary {{
    font-size: 13.5px;
    color: var(--text-dim);
    line-height: 1.5;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }}

  .team-tag {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    background: rgba(79, 195, 247, 0.12);
    color: var(--ice);
    font-size: 10.5px;
    margin-left: 6px;
  }}

  .empty-state {{
    text-align: center;
    padding: 50px 20px;
    color: var(--text-dim);
    font-size: 14px;
  }}

  @media (max-width: 480px) {{
    .digest h1 {{ font-size: 32px; }}
    .scoreboard {{ padding: 12px 16px; margin: 0 -16px; }}
    .wrap {{ padding: 0 16px 60px; }}
  }}
</style>
</head>
<body>
<div class="wrap">

  <div class="scoreboard">
    <div class="scoreboard-left">
      <span class="goal-light" aria-hidden="true"></span>
      NHL News Desk
    </div>
    <div class="scoreboard-clock">{generated_at}</div>
  </div>

  <div class="digest">
    {digest_html}
  </div>

  <div class="filters" id="filters"></div>

  <div class="section-label">Collected stories</div>
  <div id="article-list"></div>

</div>

<script>
  const ARTICLES = {articles_json};

  const listEl = document.getElementById('article-list');
  const filtersEl = document.getElementById('filters');

  function timeAgo(isoOrRfc) {{
    if (!isoOrRfc) return '';
    const d = new Date(isoOrRfc);
    if (isNaN(d)) return '';
    const diffMs = Date.now() - d.getTime();
    const mins = Math.floor(diffMs / 60000);
    if (mins < 60) return mins + 'm ago';
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return hrs + 'h ago';
    const days = Math.floor(hrs / 24);
    return days + 'd ago';
  }}

  function renderArticles(filterTeam) {{
    listEl.innerHTML = '';
    const filtered = ARTICLES.filter(a => {{
      if (!filterTeam || filterTeam === 'ALL') return true;
      return (a.teams || '').includes(filterTeam);
    }});

    if (filtered.length === 0) {{
      listEl.innerHTML = '<div class="empty-state">No stories for this filter yet.</div>';
      return;
    }}

    for (const a of filtered) {{
      const el = document.createElement('a');
      el.className = 'article';
      el.href = a.url;
      el.target = '_blank';
      el.rel = 'noopener noreferrer';

      const teamTags = (a.teams || '')
        .split(',')
        .map(t => t.trim())
        .filter(Boolean)
        .map(t => `<span class="team-tag">${{t}}</span>`)
        .join('');

      el.innerHTML = `
        <div class="article-top">
          <span>${{a.source}} &middot; ${{timeAgo(a.published || a.collected_at)}}</span>
          <span>${{teamTags}}</span>
        </div>
        <div class="article-title">${{a.title}}</div>
        <div class="article-summary">${{a.summary || ''}}</div>
      `;
      listEl.appendChild(el);
    }}
  }}

  function buildFilters() {{
    const teamSet = new Set();
    ARTICLES.forEach(a => {{
      (a.teams || '').split(',').map(t => t.trim()).filter(Boolean).forEach(t => teamSet.add(t));
    }});
    const teams = ['ALL', ...Array.from(teamSet).sort()];

    filtersEl.innerHTML = '';
    teams.forEach((team, i) => {{
      const btn = document.createElement('button');
      btn.className = 'chip' + (i === 0 ? ' active' : '');
      btn.textContent = team;
      btn.addEventListener('click', () => {{
        document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        renderArticles(team === 'ALL' ? null : team);
      }});
      filtersEl.appendChild(btn);
    }});
  }}

  buildFilters();
  renderArticles(null);
</script>
</body>
</html>
"""


def build_digest_html(digest_row):
    if not digest_row:
        return (
            '<div class="digest-eyebrow">Today\'s Digest</div>'
            '<h1>No digest yet</h1>'
            '<div class="no-digest">Run main.py with ANTHROPIC_API_KEY set to '
            'generate a curated daily digest. Raw collected stories are still '
            'listed below.</div>'
        )

    return (
        '<div class="digest-eyebrow">Today\'s Digest &middot; '
        f'{digest_row["digest_date"]}</div>'
        f'<h1>Today\'s Digest</h1>'
        f'<p>{digest_row["digest_text"]}</p>'
        f'<div class="digest-meta">Curated from {digest_row["article_count"]} stories</div>'
    )


def generate(output_path="dashboard.html"):
    db.init_db()
    with db.get_conn() as conn:
        digest_row = conn.execute(
            "SELECT * FROM daily_digests ORDER BY digest_date DESC LIMIT 1"
        ).fetchone()

        articles = conn.execute(
            "SELECT title, url, source, published, summary, teams, collected_at "
            "FROM articles ORDER BY collected_at DESC LIMIT 300"
        ).fetchall()

    articles_list = [dict(a) for a in articles]

    html = TEMPLATE.format(
        generated_at=datetime.now().strftime("%a %b %d &middot; %I:%M %p"),
        digest_html=build_digest_html(digest_row),
        articles_json=json.dumps(articles_list),
    )

    with open(output_path, "w") as f:
        f.write(html)

    print(f"Dashboard written to {output_path} ({len(articles_list)} articles)")
    return output_path


if __name__ == "__main__":
    generate()
