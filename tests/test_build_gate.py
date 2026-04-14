"""Tests for pipeline/build_gate.py — mechanical override on RU landings."""

import asyncio
import json
from pathlib import Path
from unittest.mock import patch, AsyncMock

import frontmatter
import pytest


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _write_raw(research_dir: Path, ru_landing_count: int) -> None:
    raw = {
        "buckets": {
            "DEMAND_SIGNAL": {
                "query": "купить x",
                "count": ru_landing_count,
                "ru_landing_count": ru_landing_count,
                "results": [],
            }
        }
    }
    (research_dir / "build_research_raw.json").write_text(
        json.dumps(raw), encoding="utf-8"
    )


class TestMechanicalOverride:
    def test_three_ru_landings_forces_false(self, tmp_path):
        """≥3 RU landings must flip cis_gap_confirmed to False."""
        research_dir = tmp_path / "slug"
        research_dir.mkdir()
        (research_dir / "build_research.md").write_text("build notes", encoding="utf-8")
        _write_raw(research_dir, ru_landing_count=3)

        llm_mock = AsyncMock(return_value={
            "cis_gap_confirmed": True,
            "replicable_confirmed": True,
            "oss_base_available": False,
            "market_demand_signals": True,
            "clear_localization_path": True,
        })

        with patch("pipeline.build_gate.call_llm", llm_mock):
            from pipeline.build_gate import evaluate_build

            post = frontmatter.Post("a desc", name="X", category="crm")
            result = run(evaluate_build("slug", research_dir, post, "ignored prompt"))

            assert result["cis_gap_confirmed"] is False
            assert result["_override"] == "demand_signal_ru_landings=3"

    def test_two_ru_landings_no_override(self, tmp_path):
        """<3 RU landings: LLM answer preserved."""
        research_dir = tmp_path / "slug"
        research_dir.mkdir()
        (research_dir / "build_research.md").write_text("build notes", encoding="utf-8")
        _write_raw(research_dir, ru_landing_count=2)

        llm_mock = AsyncMock(return_value={
            "cis_gap_confirmed": True,
            "replicable_confirmed": True,
            "oss_base_available": False,
            "market_demand_signals": False,
            "clear_localization_path": True,
        })

        with patch("pipeline.build_gate.call_llm", llm_mock):
            from pipeline.build_gate import evaluate_build

            post = frontmatter.Post("a desc", name="X", category="crm")
            result = run(evaluate_build("slug", research_dir, post, "ignored prompt"))

            assert result["cis_gap_confirmed"] is True
            assert "_override" not in result

    def test_missing_raw_sidecar_no_crash(self, tmp_path):
        """If build_research_raw.json is absent, gate works normally."""
        research_dir = tmp_path / "slug"
        research_dir.mkdir()
        (research_dir / "build_research.md").write_text("build notes", encoding="utf-8")
        # no sidecar written

        llm_mock = AsyncMock(return_value={
            "cis_gap_confirmed": True,
            "replicable_confirmed": False,
            "oss_base_available": False,
            "market_demand_signals": False,
            "clear_localization_path": False,
        })

        with patch("pipeline.build_gate.call_llm", llm_mock):
            from pipeline.build_gate import evaluate_build

            post = frontmatter.Post("a desc", name="X", category="crm")
            result = run(evaluate_build("slug", research_dir, post, "ignored prompt"))

            assert result["cis_gap_confirmed"] is True
            assert "_override" not in result

    def test_llm_says_false_no_override_noise(self, tmp_path):
        """If LLM already says False, override should not add spurious fields."""
        research_dir = tmp_path / "slug"
        research_dir.mkdir()
        (research_dir / "build_research.md").write_text("build notes", encoding="utf-8")
        _write_raw(research_dir, ru_landing_count=5)

        llm_mock = AsyncMock(return_value={
            "cis_gap_confirmed": False,
            "replicable_confirmed": True,
            "oss_base_available": True,
            "market_demand_signals": True,
            "clear_localization_path": True,
        })

        with patch("pipeline.build_gate.call_llm", llm_mock):
            from pipeline.build_gate import evaluate_build

            post = frontmatter.Post("a desc", name="X", category="crm")
            result = run(evaluate_build("slug", research_dir, post, "ignored prompt"))

            assert result["cis_gap_confirmed"] is False
            assert "_override" not in result
