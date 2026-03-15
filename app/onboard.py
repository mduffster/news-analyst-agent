"""Onboard new topics — generate topic brief + outcome tracker from a description."""

import re
from pathlib import Path

from app import providers

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "prompts"
TOPICS = ROOT / "topics"


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug)
    return slug[:50].rstrip("-")


async def onboard_topic(description: str, slug: str | None = None) -> str:
    """Research a topic and generate its brief + outcome tracker."""
    slug = slug or _slugify(description)
    topic_dir = TOPICS / slug

    if topic_dir.exists() and (topic_dir / "topic_brief.md").exists():
        print(f"Topic '{slug}' already exists at {topic_dir}")
        return slug

    print(f"Onboarding topic: {slug}")
    print(f"  Description: {description}")

    system_prompt = (PROMPTS / "onboarding_agent.md").read_text(encoding="utf-8")
    result = await providers.call_claude(system_prompt, description)

    # Parse response — look for fenced JSON block for outcome tracker
    content = result.content
    json_match = re.search(r"```json\s*\n(.*?)```", content, re.DOTALL)

    if json_match:
        tracker_json = json_match.group(1).strip()
        # Remove the JSON block from the brief
        brief_md = content[: json_match.start()].strip()
        # Also strip any trailing text after the JSON that's just whitespace
        trailing = content[json_match.end() :].strip()
        if trailing:
            brief_md += "\n\n" + trailing
    else:
        brief_md = content
        tracker_json = None
        print("  [WARNING] Could not extract outcome tracker JSON.")
        print("  You'll need to create outcome_tracker.json manually.")

    # Save files
    topic_dir.mkdir(parents=True, exist_ok=True)
    (topic_dir / "primers").mkdir(exist_ok=True)
    (topic_dir / "updates").mkdir(exist_ok=True)

    (topic_dir / "topic_brief.md").write_text(brief_md, encoding="utf-8")
    print(f"  Saved: topics/{slug}/topic_brief.md")

    if tracker_json:
        (topic_dir / "outcome_tracker.json").write_text(
            tracker_json, encoding="utf-8"
        )
        print(f"  Saved: topics/{slug}/outcome_tracker.json")

    print(f"\n  Review the files, then run: python run.py primers {slug}")
    return slug
