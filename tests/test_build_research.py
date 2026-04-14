"""Tests for pipeline/build_research.py — bucket labeling and RU landing detection."""

import json
from unittest.mock import patch, AsyncMock


class TestRuLandingDetection:
    def test_dot_ru_domain_counts(self):
        from pipeline.build_research import _is_ru_landing
        assert _is_ru_landing({"url": "https://shop.example.ru/crm", "title": "CRM", "text": "x"})

    def test_cyrillic_in_title_counts(self):
        from pipeline.build_research import _is_ru_landing
        assert _is_ru_landing({"url": "https://example.com/x", "title": "Купить CRM", "text": ""})

    def test_plain_com_no_cyrillic_does_not_count(self):
        from pipeline.build_research import _is_ru_landing
        assert not _is_ru_landing({"url": "https://example.com/x", "title": "Buy CRM", "text": "pricing"})


class TestBucketedFormatter:
    def test_empty_bucket_emits_zero_results_line(self):
        from pipeline.build_research import _format_bucketed, BUCKETS

        bucketed = {name: [] for name, _, _ in BUCKETS}
        out = _format_bucketed(bucketed)

        for name, _, _ in BUCKETS:
            assert f"[{name}] (0 results" in out

    def test_populated_bucket_labeled(self):
        from pipeline.build_research import _format_bucketed

        bucketed = {
            "CIS_PLAYERS": [{"title": "T", "url": "https://x.com", "text": "snip"}],
            "DEMAND_SIGNAL": [],
            "GLOBAL_ALT": [],
            "OSS_BASE": [],
            "COMMUNITY": [],
        }
        out = _format_bucketed(bucketed)

        assert "[CIS_PLAYERS] result 1: T" in out
        assert "URL: https://x.com" in out
        assert "[DEMAND_SIGNAL] (0 results" in out


class TestTimelimitRoutingOnBuckets:
    def test_cis_players_and_community_pass_y_timelimit(self):
        """CIS_PLAYERS and COMMUNITY buckets must call web_search with timelimit='y'."""
        import asyncio
        import tempfile
        from pathlib import Path

        import frontmatter

        from pipeline import build_research as br

        calls: list[dict] = []

        async def fake_search(query, num_results=5, timelimit=None):
            calls.append({"query": query, "timelimit": timelimit})
            return []

        with tempfile.TemporaryDirectory() as tmp:
            br.RESEARCH_DIR = Path(tmp)
            post = frontmatter.Post("desc", name="Acme", category="crm")

            with patch("pipeline.build_research.web_search", side_effect=fake_search), \
                 patch("pipeline.build_research.call_llm", new=AsyncMock(return_value={})), \
                 patch("pipeline.build_research.load_prompt", return_value="{bucketed_results}"):
                asyncio.new_event_loop().run_until_complete(
                    br.research_one_build(post, "acme")
                )

        by_bucket = {}
        for name, tmpl, tlimit in br.BUCKETS:
            q = tmpl.format(name="Acme", category="crm")
            match = next((c for c in calls if c["query"] == q), None)
            assert match is not None, f"no web_search call for bucket {name}"
            by_bucket[name] = match["timelimit"]

        assert by_bucket["CIS_PLAYERS"] == "y"
        assert by_bucket["COMMUNITY"] == "y"
        assert by_bucket["DEMAND_SIGNAL"] is None
        assert by_bucket["GLOBAL_ALT"] is None
        assert by_bucket["OSS_BASE"] is None


class TestSidecarOutput:
    def test_sidecar_contains_ru_landing_count(self):
        import asyncio
        import tempfile
        from pathlib import Path

        import frontmatter

        from pipeline import build_research as br

        async def fake_search(query, num_results=5, timelimit=None):
            # Only DEMAND_SIGNAL returns RU landings
            if "купить" in query or "стоимость" in query:
                return [
                    {"title": "Купить CRM", "url": "https://shop.ru/crm", "text": "цена 500р", "backend": "ddg"},
                    {"title": "CRM цена", "url": "https://x.example.ru/", "text": "тариф", "backend": "ddg"},
                    {"title": "Buy CRM", "url": "https://other.ru/crm", "text": "promo", "backend": "ddg"},
                ]
            return []

        with tempfile.TemporaryDirectory() as tmp:
            br.RESEARCH_DIR = Path(tmp)
            post = frontmatter.Post("desc", name="Acme", category="crm")

            with patch("pipeline.build_research.web_search", side_effect=fake_search), \
                 patch("pipeline.build_research.call_llm", new=AsyncMock(return_value={})), \
                 patch("pipeline.build_research.load_prompt", return_value="{bucketed_results}"):
                asyncio.new_event_loop().run_until_complete(
                    br.research_one_build(post, "acme")
                )

            sidecar = json.loads((Path(tmp) / "acme" / "build_research_raw.json").read_text())
            assert sidecar["buckets"]["DEMAND_SIGNAL"]["ru_landing_count"] == 3
            assert sidecar["buckets"]["CIS_PLAYERS"]["count"] == 0
            assert "ru_landing_count" not in sidecar["buckets"]["CIS_PLAYERS"]
