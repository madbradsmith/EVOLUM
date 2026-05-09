"""
Renders pitch deck slides as HTML using the Pitch Deck Layout System.
Slide <section> elements are filled from the manifest and assembled
into a complete deck-stage presenter page.
"""

import html
from html import escape as esc

# ── Genre detection ────────────────────────────────────────────────────────────

_GENRE_MAP = {
    "horror": "horror",
    "scary": "horror",
    "supernatural": "horror",
    "psychological": "horror",
    "sci-fi": "scifi",
    "science fiction": "scifi",
    "scifi": "scifi",
    "space": "scifi",
    "futuristic": "scifi",
    "romance": "romance",
    "romantic": "romance",
    "love": "romance",
    "comedy": "comedy",
    "comedic": "comedy",
    "funny": "comedy",
    "satire": "comedy",
    "thriller": "thriller",
    "suspense": "thriller",
    "crime": "thriller",
    "noir": "thriller",
}

def detect_deck_genre(world_or_genre: str) -> str:
    """Map a world/genre string to one of the deck-stage theme names."""
    text = (world_or_genre or "").lower()
    for keyword, theme in _GENRE_MAP.items():
        if keyword in text:
            return theme
    return "drama"  # default: warm editorial paper


# ── Slide HTML renderers ───────────────────────────────────────────────────────

def _img(url: str, style: str = "width:100%;height:100%;object-fit:cover;display:block") -> str:
    if url:
        return f'<img src="{esc(url)}" style="{style}" loading="lazy" alt="">'
    return ""


def _img_frame(url: str, label: str = "") -> str:
    inner = _img(url) if url else (
        f'<div style="position:absolute;inset:0;display:flex;align-items:center;'
        f'justify-content:center;font-family:var(--mono);font-size:20px;'
        f'color:var(--ink-mute);text-transform:uppercase;letter-spacing:.08em">'
        f'{esc(label)}</div>'
    )
    return (
        f'<div class="img-frame" style="position:relative;overflow:hidden;'
        f'background:var(--paper-dim);width:100%;height:100%">'
        f'{inner}</div>'
    )


def _render_title(title, subtitle, body, image_url, project_type, genre_tag, variant="t2"):
    """T2 (default) — Hero left: image fills left half, metadata and title on right.
       T4 — Poster-style slate with metadata stack."""
    if variant == "t4":
        img_block = _img_frame(image_url, "poster")
        logline = subtitle or body or ""
        fmt = esc(project_type or "FEATURE FILM").upper()
        genre = esc(genre_tag or "").upper()
        return f"""<section data-label="Title">
  <div class="slide-pad t4">
    <div class="top-row">
      <div class="slate">
        <div class="row"><span class="k">FORMAT</span><span class="v">{fmt}</span></div>
        {'<div class="row"><span class="k">GENRE</span><span class="v">' + genre + '</span></div>' if genre else ''}
      </div>
    </div>
    <div class="center">
      <div class="poster">{img_block}</div>
      <div class="right-block">
        <h1 class="display title">{esc(title)}</h1>
        {f'<p class="logline">{esc(logline)}</p>' if logline else ''}
      </div>
    </div>
  </div>
</section>"""
    img_block = _img_frame(image_url, "hero image")
    logline = subtitle or body or ""
    fmt = esc(project_type or "FEATURE FILM").upper()
    genre = esc(genre_tag or "").upper()
    return f"""<section data-label="Title">
  <div class="slide-pad t2">
    <div class="hero">{img_block}</div>
    <div class="meta-col">
      <div class="meta-strip">
        <span class="dot"></span>
        <span>{fmt}</span>
        {'<span class="sep"></span><span>' + genre + '</span>' if genre else ''}
      </div>
      <div>
        <h1 class="display title">{esc(title)}</h1>
        {f'<p class="logline" style="margin-top:40px">{esc(logline)}</p>' if logline else ''}
      </div>
      <div class="label">EVOLUM STUDIO &nbsp;·&nbsp; 2026</div>
    </div>
  </div>
</section>"""


def _render_logline(title, subtitle, body, image_url, project_title, genre_tag, variant="l1"):
    """L1 (default) — Massive centered serif logline.
       L2 — Accent rule, asymmetric left."""
    logline = body or subtitle or ""
    if not logline:
        logline = title
        display_title = project_title
    else:
        display_title = project_title or title
    genre = esc((genre_tag or "").upper())
    if variant == "l2":
        return f"""<section data-label="Logline">
  <div class="slide-pad l2">
    <div class="accent-rule"></div>
    <div class="label">{esc(display_title)}</div>
    <p class="logline">{esc(logline)}</p>
  </div>
</section>"""
    return f"""<section data-label="Logline">
  <div class="slide-pad l1">
    <div class="label-row">
      <div class="label">THE PITCH &nbsp;·&nbsp; ONE LINE</div>
      <div class="label">{esc(display_title)}</div>
    </div>
    <p class="logline">{esc(logline)}</p>
    {f'<div class="attribution"><div class="label">{genre}</div></div>' if genre else ''}
  </div>
</section>"""


def _render_synopsis(title, subtitle, body, image_url):
    """L2 — Accent rule with body text."""
    logline = body or subtitle or ""
    return f"""<section data-label="Synopsis">
  <div class="slide-pad l2">
    <div class="accent-rule"></div>
    <div class="label">{esc(title)}</div>
    <p class="logline">{esc(logline)}</p>
  </div>
</section>"""


def _render_protagonist(title, subtitle, body, image_url, variant="p1"):
    """P1 (default) — Half portrait: image left, name + bio right.
       P3 — Editorial spread with multiple images."""
    img_block = _img_frame(image_url, "character portrait")
    char_name = title or "THE PROTAGONIST"
    char_role = subtitle or "PROTAGONIST"
    char_bio = body or ""
    return f"""<section data-label="Character">
  <div class="slide-pad p1">
    <div class="portrait">{img_block}</div>
    <div class="info">
      <div class="label role">{esc(char_role.upper())}</div>
      <h2 class="name">{esc(char_name)}</h2>
      {f'<p class="bio">{esc(char_bio)}</p>' if char_bio else ''}
    </div>
  </div>
</section>"""


def _render_world(title, subtitle, body, image_url, variant="w3"):
    """W3 (default) — Full-bleed image with caption overlay.
       W4 — Split: image left, text details right.
       W2 — Mosaic image grid."""
    world_name = title or "THE WORLD"
    world_desc = body or subtitle or ""
    if image_url:
        img_html = _img(image_url, "width:100%;height:100%;object-fit:cover;display:block")
        return f"""<section data-label="World">
  <div class="slide-pad w3">
    <div class="bleed">{img_html}</div>
    <div class="scrim"></div>
    <div class="caption">
      <div class="label">THE WORLD</div>
      <h2 class="name">{esc(world_name)}</h2>
      {f'<p class="desc">{esc(world_desc)}</p>' if world_desc else ''}
    </div>
  </div>
</section>"""
    else:
        return f"""<section data-label="World">
  <div class="slide-pad w1">
    <div class="top">
      <h2 class="name">{esc(world_name)}</h2>
      <div class="label">THE WORLD</div>
    </div>
    {f'<p class="desc">{esc(world_desc)}</p>' if world_desc else ''}
  </div>
</section>"""


def _render_comps(title, subtitle, body, image_url, variant="c4"):
    """C4 (default) — Reference list with titles and notes.
       C1 — Two big poster comps side by side."""
    section_title = title or "COMPARABLES"
    lines = [l.strip() for l in (body or subtitle or "").split("\n") if l.strip()]
    items_html = ""
    for i, line in enumerate(lines[:4], 1):
        # Try to parse "Title — Note" or just use the whole line as the name
        if " — " in line:
            name, note = line.split(" — ", 1)
        elif " - " in line:
            name, note = line.split(" - ", 1)
        else:
            name, note = line, ""
        items_html += f"""
        <div class="item">
          <div class="num">{i:02d}</div>
          <div class="name">{esc(name.strip())}</div>
          <div class="note">{esc(note.strip())}</div>
        </div>"""
    if not items_html:
        items_html = '<div class="item"><div class="name">See attached</div></div>'
    return f"""<section data-label="Comparables">
  <div class="slide-pad c4">
    <div class="header">
      <h2 class="title">{esc(section_title)}</h2>
      <div class="label">AUDIENCE &amp; TONE</div>
    </div>
    <div class="list">{items_html}
    </div>
  </div>
</section>"""


def _render_season(title, subtitle, body, image_url):
    """S3 — Episode card grid."""
    section_title = title or "SEASON BREAKDOWN"
    lines = [l.strip() for l in (body or subtitle or "").split("\n") if l.strip()]
    cards_html = ""
    for i, line in enumerate(lines[:6], 1):
        if " — " in line:
            ep_title, ep_syn = line.split(" — ", 1)
        elif " - " in line:
            ep_title, ep_syn = line.split(" - ", 1)
        else:
            ep_title, ep_syn = f"Episode {i}", line
        cards_html += f"""
        <div class="ep-card">
          <div class="ep-num">{i:02d}</div>
          <div class="ep-title">{esc(ep_title.strip())}</div>
          {f'<div class="ep-syn">{esc(ep_syn.strip())}</div>' if ep_syn else ''}
        </div>"""
    if not cards_html:
        cards_html = f'<div class="ep-card"><div class="ep-title">{esc(section_title)}</div></div>'
    return f"""<section data-label="Season Arc">
  <div class="slide-pad s3">
    <h2 class="title">{esc(section_title)}</h2>
    <div class="ep-grid">{cards_html}
    </div>
  </div>
</section>"""


def _render_generic(stage, title, subtitle, body, image_url):
    """Generic content slide — L2 style with accent rule."""
    logline = body or subtitle or ""
    return f"""<section data-label="{esc(stage.title())}">
  <div class="slide-pad l2">
    <div class="accent-rule"></div>
    <div class="label">{esc(stage.upper())}</div>
    {f'<h2 style="font-family:var(--serif);font-size:96px;line-height:1;margin:0 0 40px">{esc(title)}</h2>' if title else ''}
    {f'<p class="logline" style="font-size:56px;line-height:1.3">{esc(logline)}</p>' if logline else ''}
    {f'<div class="hero" style="position:absolute;inset:0;z-index:-1">{_img(image_url, "width:100%;height:100%;object-fit:cover;opacity:.25")}</div>' if image_url else ''}
  </div>
</section>"""


# ── Layout hint → CSS variant map ─────────────────────────────────────────────
#
# layout_engine.py writes a `layout` field on each slide. We map that hint
# to the best CSS variant for each stage type. Falls back to the default
# variant if the hint is unrecognized or absent.
#
# layout_engine values:
#   hero_full_bleed, split_left_text, split_right_text,
#   bottom_story_card, character_focus, quote_overlay, clean_grid

_FULL_BLEED_LAYOUTS = {"hero_full_bleed", "bottom_story_card", "quote_overlay"}
_SPLIT_LAYOUTS      = {"split_left_text", "split_right_text"}
_GRID_LAYOUTS       = {"clean_grid"}
_CHAR_LAYOUTS       = {"character_focus"}


# ── Stage → renderer dispatch ─────────────────────────────────────────────────

def render_slide(slide: dict, project: dict) -> str:
    stage = (slide.get("stage") or "").upper().strip()
    layout = (slide.get("layout") or "").lower().strip()
    title = slide.get("title") or ""
    subtitle = slide.get("subtitle") or ""
    body = slide.get("body") or ""
    image_url = slide.get("image_url") or ""

    project_type = (project.get("project_type") or "FEATURE FILM").upper()
    genre_or_world = (
        project.get("genre") or project.get("world") or
        project.get("idea_genre") or ""
    )
    genre_tag = genre_or_world

    if stage == "TITLE":
        # hero_full_bleed → t2 (default); split → t4 (poster-style)
        variant = "t4" if layout in _SPLIT_LAYOUTS else "t2"
        return _render_title(title, subtitle, body, image_url, project_type, genre_tag, variant)
    elif stage == "LOGLINE":
        project_title = project.get("title") or ""
        # quote_overlay → l1 (massive centered); split → l2 (accent rule); default → l1
        variant = "l2" if layout in _SPLIT_LAYOUTS else "l1"
        return _render_logline(title, subtitle, body, image_url, project_title, genre_tag, variant)
    elif stage in ("SYNOPSIS", "OVERVIEW", "PREMISE"):
        return _render_synopsis(title, subtitle, body, image_url)
    elif stage in ("CHARACTERS", "PROTAGONIST", "CHARACTER", "CAST"):
        # character_focus / split → p1 (half portrait); clean_grid → p3 (editorial)
        variant = "p3" if layout in _GRID_LAYOUTS else "p1"
        return _render_protagonist(title, subtitle, body, image_url, variant)
    elif stage in ("WORLD", "SETTING", "TONE", "THEME", "THEMES",
                   "HOOK", "SETUP", "ESCALATION", "TURN", "AFTERMATH",
                   "CONFLICT", "STAKES", "ENGINE", "WHY_NOW", "STORY_CORE",
                   "VISUAL_INTEL", "PERFORMANCE", "SCENE_INTEL"):
        # quote_overlay / full_bleed → w3 (full-bleed scrim); split → w4; grid → w2
        if layout in _GRID_LAYOUTS:
            variant = "w2"
        elif layout in _SPLIT_LAYOUTS:
            variant = "w4"
        else:
            variant = "w3"
        return _render_world(title, subtitle, body, image_url, variant)
    elif stage in ("COMPS", "COMPARABLES", "REFERENCES", "COMP", "MARKET", "PRODUCER_READ"):
        # grid → c4 (list, default); split → c1 (two posters)
        variant = "c1" if layout in _SPLIT_LAYOUTS else "c4"
        return _render_comps(title, subtitle, body, image_url, variant)
    elif stage in ("SEASON", "ARC", "EPISODES", "BREAKDOWN", "EPISODE"):
        return _render_season(title, subtitle, body, image_url)
    else:
        return _render_generic(stage, title, subtitle, body, image_url)


# ── Full presenter page ───────────────────────────────────────────────────────

_S3_EXTRA_CSS = """
/* S3 card grid — not in the original layouts file */
.s3 { padding: 80px 100px; }
.s3 .title { font-family: var(--serif); font-size: 84px; line-height: 1; margin-bottom: 40px; }
.ep-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; flex: 1; }
.ep-card { background: var(--paper-dim); padding: 32px; display: flex; flex-direction: column; gap: 12px; }
.ep-num  { font-family: var(--mono); font-size: 20px; color: var(--accent); letter-spacing: .1em; }
.ep-title { font-family: var(--serif); font-size: 36px; line-height: 1.1; }
.ep-syn  { font-size: 22px; line-height: 1.4; color: var(--ink-soft); }
/* Override hero inside l2 */
.l2 { position: relative; }
"""

def render_deck_html(slides: list, project: dict, back_url: str = "") -> str:
    """
    Build a self-contained fullscreen HTML page using deck-stage.js.
    Returns the full HTML string to send as a response.
    back_url: URL for the ← Back button (defaults to /project/{id}/deck for V2,
              pass "/my-studio" for V1).
    """
    project_title = esc(project.get("title") or "Pitch Deck")
    genre_or_world = (
        project.get("genre") or project.get("world") or
        project.get("idea_genre") or ""
    )
    deck_genre = detect_deck_genre(genre_or_world)
    project_id = project.get("id") or ""
    resolved_back = back_url or (f"/project/{project_id}/deck" if project_id else "/")

    sections_html = "\n".join(render_slide(s, project) for s in slides)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{project_title} — Pitch Deck</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter+Tight:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>deck-stage:not(:defined){{visibility:hidden}}</style>
<link rel="stylesheet" href="/static/css/deck-layouts.css">
<style>
html, body {{ margin: 0; padding: 0; height: 100%; overflow: hidden; background: #000; }}
{_S3_EXTRA_CSS}
/* Back button overlay */
#deckBack {{
  position: fixed; top: 18px; right: 18px; z-index: 2147484000;
  background: rgba(0,0,0,0.55); border: 1px solid rgba(255,255,255,0.18);
  color: rgba(255,255,255,0.8); font-family: -apple-system, sans-serif;
  font-size: 12px; font-weight: 500; letter-spacing: 0.04em;
  padding: 7px 16px; border-radius: 999px; text-decoration: none;
  backdrop-filter: blur(8px); transition: background .15s, color .15s;
}}
#deckBack:hover {{ background: rgba(0,0,0,0.8); color: #fff; }}
</style>
<script src="/static/js/deck-stage.js" defer></script>
</head>
<body>

<a id="deckBack" href="{esc(resolved_back)}">← Back</a>

<deck-stage width="1920" height="1080" data-genre="{esc(deck_genre)}" no-rail>
{sections_html}
</deck-stage>

</body>
</html>"""
