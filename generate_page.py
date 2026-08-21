"""
Generates a static HTML dashboard (dashboard.html) from the collected
multi-sport news data. Run this any time after main.py to refresh the
page -- or call generate() from main.py to regenerate it automatically
after every collection run.

Usage:
    python generate_page.py
"""

import json
from datetime import datetime

import db
from collector import TEAM_KEYWORDS

SPORTS = list(TEAM_KEYWORDS.keys())  # e.g. ["NHL", "NFL"]

# Primary brand color per team, nested by sport (mirroring
# collector.py's TEAM_KEYWORDS structure). Nesting by sport -- rather than
# one flat dict -- matters because team NAMES can collide across leagues
# (both the NHL's Florida Panthers and the NFL's Carolina Panthers are
# just "Panthers"), so a flat dict would silently merge their colors.
TEAM_COLORS_BY_SPORT = {
    "NHL": {
        "Bruins": "#FFB81C",
        "Sabres": "#002654",
        "Red Wings": "#CE1126",
        "Panthers": "#C8102E",
        "Canadiens": "#AF1E2D",
        "Senators": "#C52032",
        "Lightning": "#002868",
        "Maple Leafs": "#00205B",
        "Hurricanes": "#CC0000",
        "Blue Jackets": "#002654",
        "Devils": "#CE1126",
        "Islanders": "#00539B",
        "Rangers": "#0038A8",
        "Flyers": "#F74902",
        "Penguins": "#FCB514",
        "Capitals": "#C8102E",
        "Blackhawks": "#CF0A2C",
        "Avalanche": "#6F263D",
        "Stars": "#006847",
        "Wild": "#154734",
        "Predators": "#FFB81C",
        "Blues": "#002F87",
        "Jets": "#041E42",
        "Coyotes": "#8C2633",
        "Ducks": "#F47A38",
        "Flames": "#C8102E",
        "Oilers": "#FF4C00",
        "Kings": "#A2AAAD",
        "Sharks": "#006D75",
        "Kraken": "#355464",
        "Canucks": "#00205B",
        "Golden Knights": "#B4975A",
    },
    "NFL": {
        "Cardinals": "#97233F",
        "Falcons": "#A71930",
        "Ravens": "#241773",
        "Bills": "#00338D",
        "Panthers": "#0085CA",
        "Bears": "#0B162A",
        "Bengals": "#FB4F14",
        "Browns": "#311D00",
        "Cowboys": "#041E42",
        "Broncos": "#FB4F14",
        "Lions": "#0076B6",
        "Packers": "#203731",
        "Texans": "#03202F",
        "Colts": "#002C5F",
        "Jaguars": "#101820",
        "Chiefs": "#E31837",
        "Raiders": "#4A4A4A",  # lightened from black for visibility as a UI accent
        "Chargers": "#0080C6",
        "Rams": "#003594",
        "Dolphins": "#008E97",
        "Vikings": "#4F2683",
        "Patriots": "#002244",
        "Saints": "#7A6628",  # darkened from gold for contrast as a UI accent
        "Giants": "#0B2265",
        "Eagles": "#004C54",
        "Steelers": "#B8860B",  # darkened from bright yellow for contrast as a UI accent
        "49ers": "#AA0000",
        "Seahawks": "#002244",
        "Buccaneers": "#D50A0A",
        "Titans": "#0C2340",
        "Commanders": "#5A1414",
    },
    "MLB": {
        "Diamondbacks": "#A71930",
        "Braves": "#CE1141",
        "Orioles": "#DF4601",
        "Red Sox": "#BD3039",
        "Cubs": "#0E3386",
        "White Sox": "#27251F",
        "Reds": "#C6011F",
        "Guardians": "#00385D",
        "Rockies": "#333366",
        "Tigers": "#0C2340",
        "Astros": "#EB6E1F",
        "Royals": "#004687",
        "Angels": "#BA0021",
        "Dodgers": "#005A9C",
        "Marlins": "#00A3E0",
        "Brewers": "#12284B",
        "Twins": "#002B5C",
        "Mets": "#002D72",
        "Yankees": "#0C2340",
        "Athletics": "#003831",
        "Phillies": "#E81828",
        "Pirates": "#FDB827",
        "Padres": "#2F241D",
        "Giants": "#FD5A1E",
        "Mariners": "#0C2C56",
        "Rays": "#092C5C",
        "Rangers": "#003278",
        "Blue Jays": "#134A8E",
        "Nationals": "#AB0003",
        "Cardinals": "#C41E3A",
    },
}

PAGE_BG_RGB = (10, 14, 19)  # matches --bg in the template CSS
WCAG_AA_TARGET = 4.5


def _hex_to_rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#{:02X}{:02X}{:02X}".format(*[max(0, min(255, round(c))) for c in rgb])


def _relative_luminance(rgb):
    def chan(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def _contrast_ratio(rgb1, rgb2):
    l1, l2 = _relative_luminance(rgb1), _relative_luminance(rgb2)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _mix_with_white(rgb, amount):
    return tuple(c + (255 - c) * amount for c in rgb)


def _lighten_until_contrast(rgb, bg_rgb, target=WCAG_AA_TARGET, max_amount=0.92):
    """Blend a color toward white in small steps until it reaches the target
    WCAG contrast ratio against bg_rgb, or hits a safety ceiling."""
    if _contrast_ratio(rgb, bg_rgb) >= target:
        return rgb
    amount = 0.0
    while amount < max_amount:
        amount += 0.02
        candidate = _mix_with_white(rgb, amount)
        if _contrast_ratio(candidate, bg_rgb) >= target:
            return candidate
    return _mix_with_white(rgb, max_amount)


def _best_text_color(bg_rgb):
    """Pick whichever of white or near-black gives better contrast against
    a given background color."""
    white, dark = (255, 255, 255), PAGE_BG_RGB
    return white if _contrast_ratio(bg_rgb, white) >= _contrast_ratio(bg_rgb, dark) else dark


def _build_accessible_color_maps():
    """
    Derives three WCAG-AA-safe (4.5:1+) color maps from TEAM_COLORS_BY_SPORT,
    nested by sport same as the input:

    - chip_colors[sport][team]: lightened-if-needed color for text/border
      on the dark page background (inactive filter chips, article tags).
    - active_text[sport][team]: white or near-black, whichever contrasts
      better as text sitting on that team's true color (active chip state).
    - tag_bg[sport][team]: a translucent (15% alpha) rgba() tint of the
      team's true color, for article-card team tag backgrounds.
    """
    chip_colors, active_text, tag_bg = {}, {}, {}
    for sport, teams in TEAM_COLORS_BY_SPORT.items():
        chip_colors[sport], active_text[sport], tag_bg[sport] = {}, {}, {}
        for team, hex_color in teams.items():
            rgb = _hex_to_rgb(hex_color)
            chip_colors[sport][team] = _rgb_to_hex(_lighten_until_contrast(rgb, PAGE_BG_RGB))
            text_rgb = _best_text_color(rgb)
            active_text[sport][team] = "#FFFFFF" if text_rgb == (255, 255, 255) else "#0A0E13"
            tag_bg[sport][team] = f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.15)"
    return chip_colors, active_text, tag_bg


TEAM_CHIP_COLORS, TEAM_ACTIVE_TEXT, TEAM_TAG_BG = _build_accessible_color_maps()


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sports Desk</title>
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

  /* --- Sport tabs --- */
  .tabs {{
    display: flex;
    gap: 4px;
    margin-top: 20px;
    border-bottom: 2px solid var(--border);
  }}

  .tab {{
    font-family: 'Teko', sans-serif;
    font-size: 20px;
    letter-spacing: 0.02em;
    text-transform: uppercase;
    padding: 8px 18px 10px;
    background: transparent;
    border: none;
    color: var(--text-dim);
    cursor: pointer;
    border-bottom: 3px solid transparent;
    margin-bottom: -2px;
    transition: color 0.15s ease, border-color 0.15s ease;
  }}

  .tab:hover {{ color: var(--text); }}

  .tab.active {{
    color: var(--ice);
    border-bottom-color: var(--ice);
  }}

  /* --- Digest hero --- */
  .digest {{
    margin-top: 24px;
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
    border: 1px solid var(--chip-color, var(--border));
    background: transparent;
    color: var(--chip-color, var(--text-dim));
    cursor: pointer;
    transition: all 0.15s ease;
    text-transform: uppercase;
  }}

  .chip:hover {{
    border-color: var(--chip-color, var(--ice));
    color: var(--text);
  }}

  .chip.active {{
    background: var(--chip-active-bg, var(--ice));
    border-color: var(--chip-active-bg, var(--ice));
    color: var(--chip-active-text, #0A0E13);
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

  .sport-badge {{
    color: var(--ice);
    font-weight: 700;
    margin-right: 6px;
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
    background: var(--tag-bg, rgba(79, 195, 247, 0.12));
    color: var(--tag-color, var(--ice));
    font-size: 10.5px;
    margin-left: 6px;
  }}

  .empty-state {{
    text-align: center;
    padding: 50px 20px;
    color: var(--text-dim);
    font-size: 14px;
  }}

  .hidden {{ display: none !important; }}

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
      Sports Desk
    </div>
    <div class="scoreboard-clock" id="scoreboard-clock" data-generated="{generated_at_iso}">Loading...</div>
  </div>

  <div class="tabs" id="tabs"></div>

  <div id="home-digest" class="digest">
    {digest_html}
  </div>

  <div class="filters hidden" id="filters"></div>

  <div class="section-label" id="section-label">Collected stories</div>
  <div id="article-list"></div>

</div>

<script>
  const ARTICLES = {articles_json};
  const SPORTS = {sports_json};
  const TEAM_COLORS = {team_colors_json};
  const TEAM_CHIP_COLORS = {team_chip_colors_json};
  const TEAM_ACTIVE_TEXT = {team_active_text_json};
  const TEAM_TAG_BG = {team_tag_bg_json};

  // Render the "last updated" clock in the *visitor's* local timezone,
  // not the server's (the page is generated on a UTC server, but each
  // viewer's browser knows their own local time).
  (function renderClock() {{
    const clockEl = document.getElementById('scoreboard-clock');
    const iso = clockEl.getAttribute('data-generated');
    const d = new Date(iso);
    if (isNaN(d)) {{
      clockEl.textContent = 'Unknown';
      return;
    }}
    const formatted = d.toLocaleString(undefined, {{
      weekday: 'short', month: 'short', day: 'numeric',
      hour: 'numeric', minute: '2-digit'
    }});
    clockEl.textContent = formatted;
  }})();

  const listEl = document.getElementById('article-list');
  const filtersEl = document.getElementById('filters');
  const digestEl = document.getElementById('home-digest');
  const sectionLabelEl = document.getElementById('section-label');
  const tabsEl = document.getElementById('tabs');

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

  // sport is required here (not inferred) because team names like
  // "Panthers" exist in more than one league -- always look colors up
  // scoped to the specific sport a given article/chip belongs to.
  function teamTagsHtml(teamsStr, sport) {{
    return (teamsStr || '')
      .split(',')
      .map(t => t.trim())
      .filter(Boolean)
      .map(t => {{
        const color = (TEAM_CHIP_COLORS[sport] || {{}})[t];
        const bg = (TEAM_TAG_BG[sport] || {{}})[t];
        const style = color && bg
          ? ` style="--tag-color: ${{color}}; --tag-bg: ${{bg}};"`
          : '';
        return `<span class="team-tag"${{style}}>${{t}}</span>`;
      }})
      .join('');
  }}

  function renderArticleCard(a, showSportBadge) {{
    const el = document.createElement('a');
    el.className = 'article';
    el.href = a.url;
    el.target = '_blank';
    el.rel = 'noopener noreferrer';

    const sportBadge = showSportBadge ? `<span class="sport-badge">${{a.sport}}</span>` : '';

    el.innerHTML = `
      <div class="article-top">
        <span>${{sportBadge}}${{a.source}} &middot; ${{timeAgo(a.published || a.collected_at)}}</span>
        <span>${{teamTagsHtml(a.teams, a.sport)}}</span>
      </div>
      <div class="article-title">${{a.title}}</div>
      <div class="article-summary">${{a.summary || ''}}</div>
    `;
    return el;
  }}

  function renderHome() {{
    digestEl.classList.remove('hidden');
    filtersEl.classList.add('hidden');
    sectionLabelEl.textContent = 'Latest across all sports';

    listEl.innerHTML = '';
    // Sort by the article's real publish time (falling back to when it
    // was collected, if publish date is missing/unparseable) rather than
    // relying on collection order -- otherwise a single run's batch (e.g.
    // "all of NHL's sources, then all of NFL's") clusters together
    // instead of genuinely interleaving by recency.
    const sorted = ARTICLES.slice().sort((a, b) => {{
      const dateA = new Date(a.published || a.collected_at);
      const dateB = new Date(b.published || b.collected_at);
      return dateB - dateA;
    }});
    const recent = sorted.slice(0, 30);
    if (recent.length === 0) {{
      listEl.innerHTML = '<div class="empty-state">No stories collected yet.</div>';
      return;
    }}
    recent.forEach(a => listEl.appendChild(renderArticleCard(a, true)));
  }}

  function renderSport(sport, filterTeam) {{
    digestEl.classList.add('hidden');
    filtersEl.classList.remove('hidden');
    sectionLabelEl.textContent = sport + ' stories';

    const sportArticles = ARTICLES.filter(a => a.sport === sport);
    const chipColors = TEAM_CHIP_COLORS[sport] || {{}};
    const trueColors = TEAM_COLORS[sport] || {{}};
    const activeText = TEAM_ACTIVE_TEXT[sport] || {{}};

    // Build filter chips scoped to just this sport's teams
    const teamSet = new Set();
    sportArticles.forEach(a => {{
      (a.teams || '').split(',').map(t => t.trim()).filter(Boolean).forEach(t => teamSet.add(t));
    }});
    const teams = ['ALL', ...Array.from(teamSet).sort()];

    filtersEl.innerHTML = '';
    teams.forEach(team => {{
      const btn = document.createElement('button');
      const isActive = (team === 'ALL' && !filterTeam) || team === filterTeam;
      btn.className = 'chip' + (isActive ? ' active' : '');
      btn.textContent = team;
      if (team !== 'ALL' && chipColors[team]) {{
        btn.style.setProperty('--chip-color', chipColors[team]);
        btn.style.setProperty('--chip-active-bg', trueColors[team]);
        btn.style.setProperty('--chip-active-text', activeText[team]);
      }}
      btn.addEventListener('click', () => {{
        renderSport(sport, team === 'ALL' ? null : team);
      }});
      filtersEl.appendChild(btn);
    }});

    const filtered = sportArticles.filter(a => {{
      if (!filterTeam) return true;
      return (a.teams || '').includes(filterTeam);
    }});

    listEl.innerHTML = '';
    if (filtered.length === 0) {{
      listEl.innerHTML = '<div class="empty-state">No stories for this filter yet.</div>';
      return;
    }}
    filtered.forEach(a => listEl.appendChild(renderArticleCard(a, false)));
  }}

  function switchTab(sport) {{
    document.querySelectorAll('.tab').forEach(t => {{
      t.classList.toggle('active', t.dataset.sport === sport);
    }});

    if (sport === 'Home') {{
      renderHome();
    }} else {{
      renderSport(sport, null);
    }}
  }}

  function buildTabs() {{
    const tabNames = ['Home', ...SPORTS];
    tabsEl.innerHTML = '';
    tabNames.forEach(sport => {{
      const btn = document.createElement('button');
      btn.className = 'tab' + (sport === 'Home' ? ' active' : '');
      btn.textContent = sport;
      btn.dataset.sport = sport;
      btn.addEventListener('click', () => switchTab(sport));
      tabsEl.appendChild(btn);
    }});
  }}

  buildTabs();
  switchTab('Home');
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
            'generate a curated daily digest across all sports. Raw collected '
            'stories are still available under each sport\'s tab.</div>'
        )

    return (
        '<div class="digest-eyebrow">Today\'s Digest &middot; '
        f'{digest_row["digest_date"]}</div>'
        f'<h1>Today\'s Digest</h1>'
        f'<p>{digest_row["digest_text"]}</p>'
        f'<div class="digest-meta">Curated from {digest_row["article_count"]} stories '
        'across all sports</div>'
    )


def generate(output_path="dashboard.html"):
    db.init_db()
    with db.get_conn() as conn:
        digest_row = conn.execute(
            "SELECT * FROM daily_digests ORDER BY digest_date DESC LIMIT 1"
        ).fetchone()

        articles = conn.execute(
            "SELECT title, url, source, published, summary, teams, sport, collected_at "
            "FROM articles ORDER BY collected_at DESC LIMIT 500"
        ).fetchall()

    articles_list = [dict(a) for a in articles]

    html = TEMPLATE.format(
        generated_at_iso=datetime.utcnow().isoformat() + "Z",
        digest_html=build_digest_html(digest_row),
        articles_json=json.dumps(articles_list),
        sports_json=json.dumps(SPORTS),
        team_colors_json=json.dumps(TEAM_COLORS_BY_SPORT),
        team_chip_colors_json=json.dumps(TEAM_CHIP_COLORS),
        team_active_text_json=json.dumps(TEAM_ACTIVE_TEXT),
        team_tag_bg_json=json.dumps(TEAM_TAG_BG),
    )

    with open(output_path, "w") as f:
        f.write(html)

    print(f"Dashboard written to {output_path} ({len(articles_list)} articles)")
    return output_path


if __name__ == "__main__":
    generate()
