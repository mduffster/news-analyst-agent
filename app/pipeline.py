"""Report generation pipeline — primers, updates, and synthesis."""

import asyncio
from datetime import date
from pathlib import Path

from app import providers

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "prompts"
TOPICS = ROOT / "topics"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _save_report(path: Path, result: providers.ProviderResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = result.content
    # Append sources if the model didn't inline them
    if result.sources and "## Sources" not in text:
        text += "\n\n## Sources\n"
        seen = set()
        for s in result.sources:
            url = s.get("url", "")
            if url and url not in seen:
                seen.add(url)
                title = s.get("title", url)
                text += f"- [{title}]({url})\n"
    path.write_text(text, encoding="utf-8")
    print(f"  Saved: {path.relative_to(ROOT)}")


def _get_latest_update_dir(slug: str) -> Path | None:
    updates_dir = TOPICS / slug / "updates"
    if not updates_dir.exists():
        return None
    dirs = sorted(
        [d for d in updates_dir.iterdir() if d.is_dir()],
        key=lambda d: d.name,
    )
    return dirs[-1] if dirs else None


async def generate_primers(topic_slug: str) -> None:
    """Generate baseline primer reports for a topic."""
    print(f"Generating primers for: {topic_slug}")

    base_role = _read(PROMPTS / "base_role.md")
    mode_primer = _read(PROMPTS / "mode_primer.md")
    topic_brief = _read(TOPICS / topic_slug / "topic_brief.md")

    system_prompt = base_role
    user_message = f"{mode_primer}\n\n---\n\n{topic_brief}"

    # Call all providers in parallel
    results = await providers.call_all(system_prompt, user_message)

    primers_dir = TOPICS / topic_slug / "primers"
    for name, result in results.items():
        _save_report(primers_dir / f"{name}.md", result)

    if len(results) < 2:
        print("  Skipping synthesis (need at least 2 provider results)")
        return

    # Synthesize
    print("  Generating primer synthesis...")
    synth_role = _read(PROMPTS / "synthesis_role.md")
    synth_mode = _read(PROMPTS / "synthesis_mode_primer.md")

    reports_text = ""
    for name, result in results.items():
        reports_text += f"\n\n## {name.capitalize()}'s Report\n\n{result.content}"

    synth_system = f"{synth_role}\n\n---\n\n{synth_mode}"
    synth_user = f"Topic brief:\n\n{topic_brief}\n\n---\n\nIndividual primer reports:{reports_text}"

    synth_result = await providers.call_synthesis(synth_system, synth_user)
    _save_report(primers_dir / "synthesis.md", synth_result)
    print("  Primers complete.")


async def generate_updates(
    topic_slug: str, date_str: str | None = None
) -> None:
    """Generate daily update reports for a topic."""
    date_str = date_str or date.today().isoformat()
    print(f"Generating update for: {topic_slug} ({date_str})")

    base_role = _read(PROMPTS / "base_role.md")
    mode_update = _read(PROMPTS / "mode_update.md")
    topic_brief = _read(TOPICS / topic_slug / "topic_brief.md")

    # Determine per-provider context: each model reads its own prior report
    latest_dir = _get_latest_update_dir(topic_slug)
    primers_dir = TOPICS / topic_slug / "primers"

    def _get_provider_context(provider_name: str) -> tuple[str, str]:
        """Return (context_text, context_label) for a specific provider."""
        if latest_dir:
            # Try this provider's own prior report first
            own_report = latest_dir / f"{provider_name}.md"
            if own_report.exists():
                return _read(own_report), f"Prior {provider_name} update ({latest_dir.name})"
            # Fall back to synthesis
            synth = latest_dir / "synthesis.md"
            if synth.exists():
                return _read(synth), f"Prior synthesis ({latest_dir.name})"
        # First update — use this provider's own primer
        own_primer = primers_dir / f"{provider_name}.md"
        if own_primer.exists():
            return _read(own_primer), f"Baseline {provider_name} primer"
        # Fall back to any primer
        for name in ("synthesis.md", "claude.md", "gpt.md"):
            p = primers_dir / name
            if p.exists():
                return _read(p), "Baseline primer"
        raise FileNotFoundError(
            f"No prior reports found for {topic_slug}. Run primers first."
        )

    # Build per-provider messages and call in parallel
    system_prompt = base_role

    async def _call_one(provider_name, call_fn):
        context, label = _get_provider_context(provider_name)
        print(f"  {provider_name}: context = {label}")
        user_message = (
            f"{mode_update}\n\n---\n\n{topic_brief}\n\n---\n\n"
            f"Your prior report for context ({label}):\n\n{context}"
        )
        return await call_fn(system_prompt, user_message)

    # Build tasks for configured providers
    from app.config import settings
    tasks = {}
    if settings.anthropic_api_key:
        tasks["claude"] = _call_one("claude", providers.call_claude)
    if settings.openai_api_key:
        tasks["gpt"] = _call_one("gpt", providers.call_gpt)
    if settings.google_api_key:
        tasks["gemini"] = _call_one("gemini", providers.call_gemini)

    if not tasks:
        raise ValueError("No AI providers configured")

    raw_results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    results = {}
    for name, result in zip(tasks.keys(), raw_results):
        if isinstance(result, Exception):
            print(f"  [ERROR] {name}: {result}")
        else:
            results[name] = result

    update_dir = TOPICS / topic_slug / "updates" / date_str
    for name, result in results.items():
        _save_report(update_dir / f"{name}.md", result)

    if len(results) < 2:
        print("  Skipping synthesis (need at least 2 provider results)")
        return

    # Synthesize — synthesis model gets the prior synthesis for its own continuity
    print("  Generating update synthesis...")
    synth_role = _read(PROMPTS / "synthesis_role.md")
    synth_mode = _read(PROMPTS / "synthesis_mode_update.md")

    prior_synthesis = ""
    if latest_dir and (latest_dir / "synthesis.md").exists():
        prior_synthesis = _read(latest_dir / "synthesis.md")
    elif (primers_dir / "synthesis.md").exists():
        prior_synthesis = _read(primers_dir / "synthesis.md")

    reports_text = ""
    for name, result in results.items():
        reports_text += f"\n\n## {name.capitalize()}'s Report\n\n{result.content}"

    synth_system = f"{synth_role}\n\n---\n\n{synth_mode}"
    synth_user = (
        f"Topic brief:\n\n{topic_brief}\n\n---\n\n"
        f"Prior synthesis for continuity:\n\n{prior_synthesis}\n\n---\n\n"
        f"Today's individual reports:{reports_text}"
    )

    synth_result = await providers.call_synthesis(synth_system, synth_user)
    _save_report(update_dir / "synthesis.md", synth_result)
    print("  Update complete.")


async def generate_all_updates(date_str: str | None = None) -> None:
    """Generate updates for all active topics."""
    for topic_dir in sorted(TOPICS.iterdir()):
        if topic_dir.is_dir() and (topic_dir / "topic_brief.md").exists():
            try:
                await generate_updates(topic_dir.name, date_str)
            except Exception as e:
                print(f"  [ERROR] {topic_dir.name}: {e}")
