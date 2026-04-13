"""Smoke tests for lib/web_search.py — all 3 backends + fallback chain."""

import asyncio
import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


# ── Helpers ──────────────────────────────────────────────────────────

def run(coro):
    """Run async function in sync test."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── DDG backend ─────────────────────────────────────────────────────

class TestDDGSearch:
    def test_ddg_success_returns_tagged_results(self):
        """DDG results should have {title, url, text, backend='ddg'}."""
        mock_raw = [
            {"title": "Result 1", "href": "https://example.com/1", "body": "snippet 1"},
            {"title": "Result 2", "href": "https://example.com/2", "body": "snippet 2"},
        ]

        mock_instance = AsyncMock()
        mock_instance.text = AsyncMock(return_value=mock_raw)

        mock_ddgs_cls = MagicMock()
        mock_ddgs_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_ddgs_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch.dict("sys.modules", {"ddgs": MagicMock(AsyncDDGS=mock_ddgs_cls)}):
            # Force reimport to pick up the mocked module
            import importlib
            import lib.web_search as ws
            importlib.reload(ws)

            results = run(ws._ddg_search("test query", num_results=2))

            assert len(results) == 2
            assert results[0]["backend"] == "ddg"
            assert results[0]["url"] == "https://example.com/1"
            assert results[0]["title"] == "Result 1"
            assert results[0]["text"] == "snippet 1"

    def test_ddg_failure_returns_empty(self):
        """DDG exception should return [], not raise."""
        with patch.dict("sys.modules", {"ddgs": MagicMock(AsyncDDGS=MagicMock(side_effect=Exception("blocked")))}):
            import importlib
            import lib.web_search as ws
            importlib.reload(ws)

            results = run(ws._ddg_search("test query"))
            assert results == []


# ── Sonar fallback ──────────────────────────────────────────────────

class TestSonarSearch:
    def test_sonar_returns_tagged_synthesized_result(self):
        """Sonar result should have backend='sonar' and [Sonar] in title."""
        mock_llm = AsyncMock(return_value="Synthesized answer about startup X")

        with patch("lib.llm.call_llm", mock_llm):
            from lib.web_search import _sonar_search
            results = run(_sonar_search("startup X funding"))

            assert len(results) == 1
            assert results[0]["backend"] == "sonar"
            assert "[Sonar]" in results[0]["title"]
            assert "Synthesized answer" in results[0]["text"]
            mock_llm.assert_called_once()
            # Verify it used perplexity/sonar model
            call_kwargs = mock_llm.call_args
            assert call_kwargs.kwargs.get("model") == "perplexity/sonar"
            assert call_kwargs.kwargs.get("json_mode") is False

    def test_sonar_failure_returns_empty(self):
        """Sonar exception should return [], not raise."""
        mock_llm = AsyncMock(side_effect=Exception("API error"))

        with patch("lib.llm.call_llm", mock_llm):
            from lib.web_search import _sonar_search
            results = run(_sonar_search("test"))
            assert results == []


# ── Exa backend ─────────────────────────────────────────────────────

class TestExaSearch:
    def test_exa_tags_results(self):
        """Exa results should get backend='exa' tag added."""
        mock_exa_results = [
            {"title": "Page 1", "url": "https://example.com", "text": "full page text"},
        ]
        # Mock the exa_client module since exa_py may not be installed
        mock_exa_module = MagicMock()
        mock_exa_module.exa_search = MagicMock(return_value=mock_exa_results)
        with patch.dict("sys.modules", {"lib.exa_client": mock_exa_module}):
            from lib.web_search import _exa_search_async
            results = run(_exa_search_async("test", num_results=1))

            assert len(results) == 1
            assert results[0]["backend"] == "exa"


# ── Fallback chain ──────────────────────────────────────────────────

class TestFallbackChain:
    def test_ddg_success_no_sonar_call(self):
        """When DDG succeeds, Sonar should NOT be called."""
        with patch.dict(os.environ, {"SEARCH_BACKEND": "ddg"}):
            with patch("lib.web_search._ddg_search", new_callable=AsyncMock,
                       return_value=[{"title": "t", "url": "u", "text": "x", "backend": "ddg"}]) as mock_ddg, \
                 patch("lib.web_search._sonar_search", new_callable=AsyncMock) as mock_sonar:

                from lib.web_search import web_search
                results = run(web_search("test"))

                assert len(results) == 1
                mock_ddg.assert_called_once()
                mock_sonar.assert_not_called()

    def test_ddg_empty_triggers_sonar_fallback(self):
        """When DDG returns [], Sonar should be called as fallback."""
        with patch.dict(os.environ, {"SEARCH_BACKEND": "ddg"}):
            with patch("lib.web_search._ddg_search", new_callable=AsyncMock,
                       return_value=[]) as mock_ddg, \
                 patch("lib.web_search._sonar_search", new_callable=AsyncMock,
                       return_value=[{"title": "t", "url": "", "text": "sonar answer", "backend": "sonar"}]) as mock_sonar:

                from lib.web_search import web_search
                results = run(web_search("test"))

                assert len(results) == 1
                assert results[0]["backend"] == "sonar"
                mock_ddg.assert_called_once()
                mock_sonar.assert_called_once()

    def test_both_fail_returns_empty(self):
        """When both DDG and Sonar fail, return []."""
        with patch.dict(os.environ, {"SEARCH_BACKEND": "ddg"}):
            with patch("lib.web_search._ddg_search", new_callable=AsyncMock, return_value=[]), \
                 patch("lib.web_search._sonar_search", new_callable=AsyncMock, return_value=[]):

                from lib.web_search import web_search
                results = run(web_search("test"))
                assert results == []

    def test_exa_backend_no_fallback(self):
        """SEARCH_BACKEND=exa should call Exa only, no DDG/Sonar."""
        with patch.dict(os.environ, {"SEARCH_BACKEND": "exa"}):
            with patch("lib.web_search._exa_search_async", new_callable=AsyncMock,
                       return_value=[{"title": "t", "url": "u", "text": "x", "backend": "exa"}]) as mock_exa, \
                 patch("lib.web_search._ddg_search", new_callable=AsyncMock) as mock_ddg:

                from lib.web_search import web_search
                results = run(web_search("test"))

                assert results[0]["backend"] == "exa"
                mock_exa.assert_called_once()
                mock_ddg.assert_not_called()


# ── Output contract ─────────────────────────────────────────────────

class TestOutputContract:
    def test_all_backends_have_required_fields(self):
        """Every result from any backend must have title, url, text, backend."""
        required = {"title", "url", "text", "backend"}

        # DDG result
        mock_instance = AsyncMock()
        mock_instance.text = AsyncMock(return_value=[{"title": "t", "href": "u", "body": "b"}])

        mock_ddgs_cls = MagicMock()
        mock_ddgs_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_ddgs_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch.dict("sys.modules", {"ddgs": MagicMock(AsyncDDGS=mock_ddgs_cls)}):
            import importlib
            import lib.web_search as ws
            importlib.reload(ws)

            for r in run(ws._ddg_search("q")):
                assert required <= set(r.keys()), f"DDG result missing fields: {required - set(r.keys())}"

        # Sonar result
        mock_llm = AsyncMock(return_value="answer")
        with patch("lib.llm.call_llm", mock_llm):
            from lib.web_search import _sonar_search
            for r in run(_sonar_search("q")):
                assert required <= set(r.keys()), f"Sonar result missing fields: {required - set(r.keys())}"
