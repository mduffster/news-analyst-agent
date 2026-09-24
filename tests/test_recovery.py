"""Regression coverage for incomplete daily reports, without API calls."""

import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from urllib.parse import urlsplit

from app import build, pipeline, providers
from app.config import settings
from app.providers import ProviderResult


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.hrefs.extend(value for key, value in attrs if key == "href")


class ProviderReportTests(unittest.IsolatedAsyncioTestCase):
    async def test_title_is_preserved_when_report_has_no_preamble(self):
        report = "# Report title\n\n## September 24, 2026\n\nAnalysis."
        for prefix in ("", "\n  ", "Here is the report:\n"):
            with self.subTest(prefix=prefix), patch.object(providers.anthropic, "AsyncAnthropic") as client:
                client.return_value.messages.create = AsyncMock(return_value=SimpleNamespace(
                    content=[SimpleNamespace(type="text", text=prefix + report)]
                ))
                result = await providers.call_claude("system", "user")
                self.assertEqual(result.content.strip(), report)


class SiteRecoveryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.topics = self.root / "topics"
        self.site = self.root / "site"
        for name, value in (("ROOT", self.root), ("TOPICS", self.topics), ("SITE", self.site)):
            patcher = patch.object(build, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.write("topic_brief.md", "# Test topic")
        self.write("primers/gpt.md", "# Baseline")
        for page in ("about", "feedback"):
            (self.root / f"{page}.md").write_text(f"# {page}")

    def write(self, relative, text):
        path = self.topics / "test" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def assert_local_links_resolve(self):
        for page in self.site.rglob("*.html"):
            parser = Links()
            parser.feed(page.read_text())
            for href in parser.hrefs:
                url = urlsplit(href)
                if url.scheme or url.netloc or not url.path:
                    continue
                self.assertTrue((page.parent / url.path).exists(), f"{page}: {href}")

    def test_latest_partial_report_and_archive_remain_accessible(self):
        self.write("updates/2026-09-17/synthesis.md", "# Older synthesis")
        self.write("updates/2026-09-24/gpt.md", "# Current GPT report")
        build.build_site()
        home = (self.site / "test/index.html").read_text()
        self.assertIn("Current GPT report", home)
        self.assertIn("Synthesis is unavailable for 2026-09-24", home)
        self.assertIn('href="2026-09-24/gpt.html"', home)
        self.assertIn('href="2026-09-17/synthesis.html"', home)
        self.assertNotIn("No updates yet", home)
        self.assert_local_links_resolve()

    def test_complete_day_prefers_synthesis(self):
        self.write("updates/2026-09-24/gpt.md", "# Current GPT report")
        self.write("updates/2026-09-24/synthesis.md", "# Current synthesis")
        build.build_site()
        home = (self.site / "test/index.html").read_text()
        self.assertIn("Current synthesis", home)
        self.assertNotIn("Synthesis is unavailable", home)
        self.assert_local_links_resolve()

    def test_empty_latest_day_keeps_previous_report(self):
        self.write("updates/2026-09-17/synthesis.md", "# Last complete report")
        self.write("updates/2026-09-24/synthesis.md", " \n")
        build.build_site()
        home = (self.site / "test/index.html").read_text()
        self.assertIn("Last complete report", home)
        self.assertNotIn("2026-09-24/", home)
        self.assert_local_links_resolve()

    def test_gemini_only_day_is_accessible(self):
        self.write("updates/2026-09-24/gemini.md", "# Gemini report")
        build.build_site()
        home = (self.site / "test/index.html").read_text()
        self.assertIn("Gemini report", home)
        self.assertIn("Showing the Gemini report", home)
        self.assert_local_links_resolve()


class PipelineRecoveryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.topics = self.root / "topics"
        self.day = self.topics / "test/updates/2026-09-24"
        for name, value in (("ROOT", self.root), ("TOPICS", self.topics)):
            patcher = patch.object(pipeline, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        for name, value in (("anthropic_api_key", "test"), ("openai_api_key", "test"), ("google_api_key", "")):
            patcher = patch.object(settings, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.add_topic("test")
        self.claude = self.mock_provider("call_claude", "# Claude report")
        self.gpt = self.mock_provider("call_gpt", "# GPT report")
        self.synthesis = self.mock_provider("call_synthesis", "# Synthesis report")
        sleeper = patch.object(pipeline.asyncio, "sleep", new_callable=AsyncMock)
        sleeper.start()
        self.addCleanup(sleeper.stop)

    def add_topic(self, slug):
        topic = self.topics / slug
        (topic / "primers").mkdir(parents=True)
        (topic / "topic_brief.md").write_text("# Test topic")
        (topic / "primers/gpt.md").write_text("# Baseline report")

    def mock_provider(self, name, content):
        patcher = patch.object(pipeline.providers, name, new_callable=AsyncMock)
        mock = patcher.start()
        self.addCleanup(patcher.stop)
        mock.return_value = ProviderResult(content=content)
        return mock

    async def test_credit_failure_saves_gpt_and_fails_run(self):
        self.claude.side_effect = RuntimeError("credit balance is too low")
        with self.assertRaisesRegex(RuntimeError, "Daily updates incomplete"):
            await pipeline.generate_all_updates("2026-09-24")
        self.assertEqual((self.day / "gpt.md").read_text(), "# GPT report")
        self.assertFalse((self.day / "synthesis.md").exists())
        self.synthesis.assert_not_awaited()

    async def test_empty_provider_response_is_not_published(self):
        self.claude.return_value = ProviderResult(content=" \n")
        with self.assertRaisesRegex(RuntimeError, "Daily updates incomplete"):
            await pipeline.generate_all_updates("2026-09-24")
        self.assertTrue((self.day / "gpt.md").exists())
        self.assertFalse((self.day / "claude.md").exists())
        self.synthesis.assert_not_awaited()

    async def test_all_providers_fail(self):
        self.claude.side_effect = RuntimeError("provider unavailable")
        self.gpt.side_effect = RuntimeError("provider unavailable")
        with self.assertRaisesRegex(RuntimeError, "Daily updates incomplete"):
            await pipeline.generate_all_updates("2026-09-24")
        self.assertFalse(self.day.exists())

    async def test_synthesis_failure_preserves_individual_reports(self):
        self.synthesis.side_effect = RuntimeError("synthesis unavailable")
        with self.assertRaisesRegex(RuntimeError, "Daily updates incomplete"):
            await pipeline.generate_all_updates("2026-09-24")
        self.assertTrue((self.day / "claude.md").exists())
        self.assertTrue((self.day / "gpt.md").exists())
        self.assertFalse((self.day / "synthesis.md").exists())

    async def test_empty_synthesis_does_not_replace_existing_report(self):
        self.day.mkdir(parents=True)
        (self.day / "synthesis.md").write_text("# Existing synthesis")
        self.synthesis.return_value = ProviderResult(content="")
        with self.assertRaisesRegex(RuntimeError, "Daily updates incomplete"):
            await pipeline.generate_all_updates("2026-09-24")
        self.assertEqual((self.day / "synthesis.md").read_text(), "# Existing synthesis")

    async def test_other_topics_are_attempted_before_run_fails(self):
        self.add_topic("second")
        self.claude.side_effect = RuntimeError("credit balance is too low")
        with self.assertRaisesRegex(RuntimeError, "second, test"):
            await pipeline.generate_all_updates("2026-09-24")
        self.assertEqual(self.gpt.await_count, 2)

    async def test_successful_run_saves_synthesis(self):
        await pipeline.generate_all_updates("2026-09-24")
        self.assertEqual((self.day / "synthesis.md").read_text(), "# Synthesis report")

    async def test_context_survives_incomplete_days_and_excludes_current_and_future(self):
        updates = self.topics / "test/updates"
        reports = {
            "2026-09-17/claude.md": "# Last complete Claude report",
            "2026-09-17/synthesis.md": "# Last complete synthesis",
            "2026-09-23/gpt.md": "# Latest GPT report",
            "2026-09-23/synthesis.md": " \n",
            "2026-09-24/synthesis.md": "# Same-day synthesis to replace",
            "2026-09-25/synthesis.md": "# Future synthesis",
            "drafts/synthesis.md": "# Undated draft",
        }
        for relative, content in reports.items():
            path = updates / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)

        await pipeline.generate_all_updates("2026-09-24")

        claude_context = self.claude.await_args.args[1]
        self.assertIn("Prior claude update (2026-09-17)", claude_context)
        self.assertIn("# Last complete Claude report", claude_context)
        gpt_context = self.gpt.await_args.args[1]
        self.assertIn("Prior gpt update (2026-09-23)", gpt_context)
        self.assertIn("# Latest GPT report", gpt_context)
        synth_context = self.synthesis.await_args.args[1]
        self.assertIn("Report date: 2026-09-24", synth_context)
        self.assertIn("Last available synthesis (2026-09-17)", synth_context)
        self.assertIn("# Last complete synthesis", synth_context)
        for excluded in ("Same-day synthesis to replace", "Future synthesis", "Undated draft"):
            self.assertNotIn(excluded, synth_context)

    async def test_backfill_uses_only_reports_before_requested_date(self):
        for day in ("2026-09-15", "2026-09-17"):
            directory = self.topics / "test/updates" / day
            directory.mkdir(parents=True)
            (directory / "synthesis.md").write_text(f"# Synthesis {day}")
        await pipeline.generate_all_updates("2026-09-16")
        context = self.synthesis.await_args.args[1]
        self.assertIn("Last available synthesis (2026-09-15)", context)
        self.assertNotIn("2026-09-17", context)

    async def test_first_update_labels_primer_context(self):
        primer = self.topics / "test/primers/synthesis.md"
        primer.write_text("# Primer synthesis")
        await pipeline.generate_all_updates("2026-09-24")
        context = self.synthesis.await_args.args[1]
        self.assertIn("Baseline primer synthesis", context)
        self.assertIn("# Primer synthesis", context)


if __name__ == "__main__":
    unittest.main()
