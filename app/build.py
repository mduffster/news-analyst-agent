"""Build static HTML site from markdown reports."""

import shutil
from datetime import date
from pathlib import Path

import jinja2
import markdown
from markupsafe import Markup

ROOT = Path(__file__).resolve().parent.parent
TOPICS = ROOT / "topics"
SITE = ROOT / "site"

MD = markdown.Markdown(extensions=["tables", "fenced_code", "toc"])

BASE_TEMPLATE = """<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} — News Analyst</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
    <style>
        .report-nav { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1.5rem; }
        .report-nav a {
            padding: 0.3rem 0.75rem; border-radius: 4px;
            text-decoration: none; font-size: 0.85em;
            border: 1px solid var(--pico-muted-border-color);
        }
        .report-nav a.active {
            background: var(--pico-primary-background);
            color: var(--pico-primary-inverse);
            border-color: var(--pico-primary-background);
        }
        .sidebar { font-size: 0.85em; border-left: 2px solid var(--pico-muted-border-color); padding-left: 1rem; }
        .sidebar h4 { margin-bottom: 0.5rem; }
        .sidebar ul { list-style: none; padding: 0; margin: 0; }
        .sidebar li { margin-bottom: 0.25rem; }
        .sidebar .provider-links { font-size: 0.85em; opacity: 0.7; }
        .sidebar .provider-links a { margin-left: 0.25rem; }
        .layout { display: grid; grid-template-columns: 1fr 220px; gap: 2rem; align-items: start; }
        @media (max-width: 768px) { .layout { grid-template-columns: 1fr; } }
        table { font-size: 0.9em; }
        article.report { max-width: 100%; overflow-x: auto; }
    </style>
</head>
<body>
<nav class="container">
    <ul><li><a href="{{ base }}"><strong>News Analyst</strong></a></li></ul>
</nav>
<main class="container">
    {{ content }}
</main>
<footer class="container">
    <small>Built {{ build_date }}</small>
</footer>
</body>
</html>"""

_jinja_env = jinja2.Environment(autoescape=True)
_template = _jinja_env.from_string(BASE_TEMPLATE)


def _md_to_html(md_text: str) -> str:
    MD.reset()
    return MD.convert(md_text)


def _get_topic_title(slug: str) -> str:
    brief_path = TOPICS / slug / "topic_brief.md"
    if brief_path.exists():
        for line in brief_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    return slug.replace("-", " ").title()


def _depth_to_base(depth: int) -> str:
    if depth == 0:
        return "."
    return "/".join([".."] * depth)


def _render(path: Path, title: str, content_html: str, depth: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    html = _template.render(
        title=title,
        content=Markup(content_html),
        base=_depth_to_base(depth),
        build_date=date.today().isoformat(),
    )
    path.write_text(html, encoding="utf-8")


def _provider_nav(current: str, names: list[str], path_prefix: str) -> str:
    links = []
    for name in names:
        cls = ' class="active"' if name == current else ""
        label = "Synthesis" if name == "synthesis" else name.capitalize()
        links.append(f'<a href="{path_prefix}{name}.html"{cls}>{label}</a>')
    return '<div class="report-nav">' + "".join(links) + "</div>"


def _build_sidebar(slug: str, title: str, update_dates: list[str], primers_dir: Path, updates_dir: Path, current_date: str | None = None) -> str:
    """Build the right sidebar with archive links."""
    parts = ['<aside class="sidebar">']

    # Primer links
    if primers_dir.exists() and any(primers_dir.glob("*.md")):
        parts.append("<h4>Primer</h4><ul>")
        if (primers_dir / "synthesis.md").exists():
            parts.append('<li><a href="primer.html">Synthesis</a></li>')
        for name in ("claude", "gpt"):
            if (primers_dir / f"{name}.md").exists():
                parts.append(f'<li><a href="primers/{name}.html">{name.capitalize()}</a></li>')
        parts.append("</ul>")

    # Update archive
    if update_dates:
        parts.append("<h4>Updates</h4><ul>")
        for d in update_dates:
            active = " <strong>&larr;</strong>" if d == current_date else ""
            line = f'<li><a href="{d}/synthesis.html">{d}</a>{active}'
            plinks = []
            for name in ("claude", "gpt"):
                if (updates_dir / d / f"{name}.md").exists():
                    plinks.append(f'<a href="{d}/{name}.html">{name.capitalize()}</a>')
            if plinks:
                line += ' <span class="provider-links">' + " | ".join(plinks) + "</span>"
            line += "</li>"
            parts.append(line)
        parts.append("</ul>")

    parts.append("</aside>")
    return "\n".join(parts)


def build_site(output_dir: str = "site") -> None:
    global SITE
    SITE = ROOT / output_dir

    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir(parents=True)

    topics = []
    for topic_dir in sorted(TOPICS.iterdir()):
        if not topic_dir.is_dir() or not (topic_dir / "topic_brief.md").exists():
            continue
        slug = topic_dir.name
        title = _get_topic_title(slug)
        topics.append((slug, title))
        _build_topic(slug, title)

    # Home page — if single topic, redirect to it; if multiple, show list
    if len(topics) == 1:
        slug, title = topics[0]
        # Just render the topic index as the home page too
        redirect = f'<meta http-equiv="refresh" content="0;url={slug}/">'
        (SITE / "index.html").write_text(
            f'<!DOCTYPE html><html><head>{redirect}</head><body>Redirecting to <a href="{slug}/">{title}</a></body></html>',
            encoding="utf-8",
        )
    else:
        items_html = ""
        for slug, title in topics:
            items_html += f'<article><h3><a href="{slug}/">{title}</a></h3></article>\n'
        index_html = f"<h1>News Analyst</h1>\n<p>AI-powered intelligence analysis.</p>\n{items_html}"
        _render(SITE / "index.html", "Home", index_html, 0)

    print(f"Built site with {len(topics)} topic(s) at {SITE}")


def _build_topic(slug: str, title: str):
    topic_dir = TOPICS / slug
    primers_dir = topic_dir / "primers"
    updates_dir = topic_dir / "updates"

    # Collect update dates
    update_dates = []
    if updates_dir.exists():
        update_dates = sorted(
            [d.name for d in updates_dir.iterdir() if d.is_dir()], reverse=True
        )

    # --- Topic index: render latest synthesis inline ---
    latest_content = ""
    latest_date = None
    if update_dates:
        latest_date = update_dates[0]
        synth_path = updates_dir / latest_date / "synthesis.md"
        if synth_path.exists():
            latest_content = synth_path.read_text(encoding="utf-8")

    if latest_content:
        # Show latest synthesis directly, with nav to individual reports
        providers_available = [
            n for n in ("synthesis", "claude", "gpt")
            if (updates_dir / latest_date / f"{n}.md").exists()
        ]
        nav = _provider_nav("synthesis", providers_available, f"{latest_date}/")
        # Fix synthesis link to point to self (we're showing it inline)
        nav = nav.replace(f'href="{latest_date}/synthesis.html"', 'href="#"')

        sidebar = _build_sidebar(slug, title, update_dates, primers_dir, updates_dir, latest_date)
        report_html = _md_to_html(latest_content)

        content = f'<div class="layout"><div>{nav}{report_html}</div>{sidebar}</div>'
    else:
        # No updates yet — show primer or placeholder
        content = f"<h1>{title}</h1><p>No updates yet.</p>"

    _render(SITE / slug / "index.html", title, content, 1)

    # --- Primer pages ---
    if primers_dir.exists():
        providers_available = [
            n for n in ("synthesis", "claude", "gpt")
            if (primers_dir / f"{n}.md").exists()
        ]

        if (primers_dir / "synthesis.md").exists():
            md_text = (primers_dir / "synthesis.md").read_text(encoding="utf-8")
            nav = _provider_nav("synthesis", providers_available, "primers/")
            nav = nav.replace('href="primers/synthesis.html"', 'href="primer.html"')
            sidebar = _build_sidebar(slug, title, update_dates, primers_dir, updates_dir)
            report_html = _md_to_html(md_text)
            content = f'<div class="layout"><div>{nav}{report_html}</div>{sidebar}</div>'
            _render(SITE / slug / "primer.html", f"{title} — Primer", content, 1)

        for name in ("claude", "gpt"):
            md_path = primers_dir / f"{name}.md"
            if not md_path.exists():
                continue
            md_text = md_path.read_text(encoding="utf-8")
            nav = _provider_nav(name, providers_available, "")
            nav = nav.replace('href="synthesis.html"', 'href="../primer.html"')
            sidebar = _build_sidebar(slug, title, update_dates, primers_dir, updates_dir)
            # Fix sidebar paths — we're one level deeper
            sidebar = sidebar.replace('href="primer.html"', 'href="../primer.html"')
            sidebar = sidebar.replace('href="primers/', 'href="')
            for d in update_dates:
                sidebar = sidebar.replace(f'href="{d}/', f'href="../{d}/')
            report_html = _md_to_html(md_text)
            content = f'<div class="layout"><div>{nav}{report_html}</div>{sidebar}</div>'
            _render(
                SITE / slug / "primers" / f"{name}.html",
                f"{title} — Primer ({name.capitalize()})",
                content,
                2,
            )

    # --- Update pages ---
    for d in update_dates:
        day_dir = updates_dir / d
        providers_available = [
            n for n in ("synthesis", "claude", "gpt")
            if (day_dir / f"{n}.md").exists()
        ]

        for name in providers_available:
            md_path = day_dir / f"{name}.md"
            md_text = md_path.read_text(encoding="utf-8")
            nav = _provider_nav(name, providers_available, "")
            sidebar = _build_sidebar(slug, title, update_dates, primers_dir, updates_dir, d)
            # Fix sidebar paths — we're one level deeper
            sidebar = sidebar.replace('href="primer.html"', 'href="../primer.html"')
            sidebar = sidebar.replace('href="primers/', 'href="../primers/')
            for dd in update_dates:
                if f'href="{dd}/' in sidebar:
                    sidebar = sidebar.replace(f'href="{dd}/', f'href="../{dd}/')
            report_html = _md_to_html(md_text)
            label = "Synthesis" if name == "synthesis" else name.capitalize()
            content = f'<div class="layout"><div>{nav}{report_html}</div>{sidebar}</div>'
            _render(
                SITE / slug / d / f"{name}.html",
                f"{title} — {d} ({label})",
                content,
                2,
            )
