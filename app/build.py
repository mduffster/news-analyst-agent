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
        .report-nav { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1rem; }
        .report-nav a { padding: 0.25rem 0.75rem; border-radius: 4px; text-decoration: none; }
        .report-nav a.active { background: var(--pico-primary-background); color: var(--pico-primary-inverse); }
        .update-list { list-style: none; padding: 0; }
        .update-list li { margin-bottom: 0.5rem; }
        .provider-links { display: inline; font-size: 0.85em; }
        .provider-links a { margin-left: 0.5rem; }
        table { font-size: 0.9em; }
        article.report { max-width: 100%; overflow-x: auto; }
    </style>
</head>
<body>
<nav class="container">
    <ul><li><a href="{{ base }}"><strong>News Analyst</strong></a></li></ul>
</nav>
<main class="container">
    <nav aria-label="breadcrumb" style="font-size:0.9em; margin-bottom:1rem;">
        {{ breadcrumb }}
    </nav>
    <article class="report">
        {{ content }}
    </article>
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
    """Return relative path prefix to site root."""
    if depth == 0:
        return "."
    return "/".join([".."] * depth)


def _render(path: Path, title: str, content_html: str, breadcrumb: str, depth: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    html = _template.render(
        title=title,
        content=Markup(content_html),
        breadcrumb=Markup(breadcrumb),
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

    # Build index
    items_html = ""
    for slug, title in topics:
        items_html += f'<article><h3><a href="{slug}/">{title}</a></h3></article>\n'

    index_html = f"<h1>News Analyst</h1>\n<p>AI-powered intelligence analysis with multi-model comparison.</p>\n{items_html}"
    _render(SITE / "index.html", "Home", index_html, "", 0)
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

    bc_topic = f'<a href="{_depth_to_base(1)}">Home</a> &rsaquo; {title}'

    # --- Topic index page ---
    index_parts = [f"<h1>{title}</h1>"]

    # Latest synthesis link
    if update_dates:
        latest = update_dates[0]
        index_parts.append(
            f'<p><strong>Latest:</strong> <a href="{latest}/synthesis.html">{latest} Synthesis</a></p>'
        )

    # Primer section
    if primers_dir.exists() and any(primers_dir.glob("*.md")):
        index_parts.append("<h2>Primer</h2>")
        if (primers_dir / "synthesis.md").exists():
            index_parts.append(
                '<p><a href="primer.html">Read Primer Synthesis</a></p>'
            )
        provider_links = []
        for name in ("claude", "gpt", "gemini"):
            if (primers_dir / f"{name}.md").exists():
                label = name.capitalize()
                provider_links.append(
                    f'<a href="primers/{name}.html">{label}</a>'
                )
        if provider_links:
            index_parts.append(
                "<p>Individual reports: " + " | ".join(provider_links) + "</p>"
            )

    # Updates archive
    if update_dates:
        index_parts.append("<h2>Updates</h2><ul class='update-list'>")
        for d in update_dates:
            line = f'<li><a href="{d}/synthesis.html">{d}</a>'
            plinks = []
            for name in ("claude", "gpt", "gemini"):
                if (updates_dir / d / f"{name}.md").exists():
                    plinks.append(f'<a href="{d}/{name}.html">{name.capitalize()}</a>')
            if plinks:
                line += ' <span class="provider-links">(' + " | ".join(plinks) + ")</span>"
            line += "</li>"
            index_parts.append(line)
        index_parts.append("</ul>")

    _render(
        SITE / slug / "index.html",
        title,
        "\n".join(index_parts),
        bc_topic,
        1,
    )

    # --- Primer pages ---
    if primers_dir.exists():
        providers_available = [
            n for n in ("synthesis", "claude", "gpt", "gemini")
            if (primers_dir / f"{n}.md").exists()
        ]

        # Primer synthesis → primer.html
        if (primers_dir / "synthesis.md").exists():
            md_text = (primers_dir / "synthesis.md").read_text(encoding="utf-8")
            nav = _provider_nav("synthesis", providers_available, "primers/")
            # synthesis link points to self at primer.html
            nav = nav.replace('href="primers/synthesis.html"', 'href="primer.html"')
            content = nav + _md_to_html(md_text)
            bc = f'<a href="{_depth_to_base(1)}">Home</a> &rsaquo; <a href=".">{title}</a> &rsaquo; Primer'
            _render(SITE / slug / "primer.html", f"{title} — Primer", content, bc, 1)

        # Individual primer reports
        for name in ("claude", "gpt", "gemini"):
            md_path = primers_dir / f"{name}.md"
            if not md_path.exists():
                continue
            md_text = md_path.read_text(encoding="utf-8")
            nav = _provider_nav(name, providers_available, "")
            nav = nav.replace('href="synthesis.html"', 'href="../primer.html"')
            content = nav + _md_to_html(md_text)
            bc = (
                f'<a href="{_depth_to_base(2)}">Home</a> &rsaquo; '
                f'<a href="..">{title}</a> &rsaquo; '
                f'<a href="../primer.html">Primer</a> &rsaquo; {name.capitalize()}'
            )
            _render(
                SITE / slug / "primers" / f"{name}.html",
                f"{title} — Primer ({name.capitalize()})",
                content,
                bc,
                2,
            )

    # --- Update pages ---
    for d in update_dates:
        day_dir = updates_dir / d
        providers_available = [
            n for n in ("synthesis", "claude", "gpt", "gemini")
            if (day_dir / f"{n}.md").exists()
        ]

        for name in providers_available:
            md_path = day_dir / f"{name}.md"
            md_text = md_path.read_text(encoding="utf-8")
            nav = _provider_nav(name, providers_available, "")
            content = nav + _md_to_html(md_text)
            label = "Synthesis" if name == "synthesis" else name.capitalize()
            bc = (
                f'<a href="{_depth_to_base(2)}">Home</a> &rsaquo; '
                f'<a href="..">{title}</a> &rsaquo; '
                f'{d} &rsaquo; {label}'
            )
            _render(
                SITE / slug / d / f"{name}.html",
                f"{title} — {d} ({label})",
                content,
                bc,
                2,
            )
