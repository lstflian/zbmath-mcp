"""Tests for zbmath-mcp server tools."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

# Shapes mirror the live zbMath Open REST API (verified 2026): "keywords" is a
# flat list of strings, MSC codes live in a top-level "msc" list, the canonical
# link is "zbmath_url", and "year" is a string.
MOCK_SEARCH_RESPONSE = {
    "status": {"nr_total_results": 2},
    "result": [
        {
            "id": 7192477,
            "title": {"title": "On the Riemann hypothesis"},
            "contributors": {"authors": [{"name": "Doe, John"}]},
            "year": "2020",
            "source": {"series": [{"title": "Annals of Mathematics"}], "source": "Ann. Math. (2020)."},
            "keywords": ["Riemann hypothesis", "zeta function"],
            "msc": [{"code": "11M26", "scheme": "msc2020", "text": "Nonreal zeros"}],
            "editorial_contributions": [{"text": "A great paper."}],
            "zbmath_url": "https://zbmath.org/7192477",
        },
        {
            "id": 1234567,
            "title": {"title": "Spectral theory"},
            "contributors": {"authors": [{"name": "Smith, Jane"}]},
            "year": "2019",
            "source": {"series": []},
            "keywords": [],
            "msc": [{"code": "35P15", "scheme": "msc2020", "text": "Estimates of eigenvalues"}],
            "editorial_contributions": [],
            "zbmath_url": "https://zbmath.org/1234567",
        },
    ],
}

# A well-formed query with no matches: the API replies HTTP 404 with this body.
MOCK_ZERO_RESULTS_RESPONSE = {
    "result": None,
    "status": {
        "execution": "Entry not found!",
        "internal_code": "successful access. Zero results.",
        "nr_total_results": None,
        "status_code": 404,
    },
}

MOCK_DOCUMENT_RESPONSE = {
    "result": {
        "id": 7192477,
        "title": {"title": "On the Riemann hypothesis"},
        "contributors": {"authors": [{"name": "Doe, John"}]},
        "year": 2020,
    }
}

MOCK_AUTHOR_RESPONSE = {
    "result": {
        "id": "euler.leonhard",
        "name": "Euler, Leonhard",
        "publications": 866,
    }
}

MOCK_SOFTWARE_RESPONSE = {
    "result": {
        "id": 825,
        "name": "Macaulay2",
        "description": "A software system for algebraic geometry.",
    }
}


# ---------------------------------------------------------------------------
# Patch helper
# ---------------------------------------------------------------------------

def _make_mock_http_response(data: dict, status_code: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.raise_for_status = MagicMock()
    mock.json = MagicMock(return_value=data)
    return mock


# ---------------------------------------------------------------------------
# Tests for search_documents
# ---------------------------------------------------------------------------

class TestSearchDocuments:
    @pytest.mark.asyncio
    async def test_returns_documents(self):
        from server import search_documents

        mock_response = _make_mock_http_response(MOCK_SEARCH_RESPONSE)
        with patch("server.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await search_documents("Riemann hypothesis")

        data = json.loads(result)
        assert data["total_results"] == 2
        assert len(data["documents"]) == 2
        assert data["documents"][0]["zbmath_id"] == 7192477
        assert data["documents"][0]["title"] == "On the Riemann hypothesis"
        assert data["documents"][0]["authors"] == ["Doe, John"]
        assert data["documents"][0]["msc_codes"] == ["11M26"]
        assert data["documents"][0]["keywords"] == ["Riemann hypothesis", "zeta function"]
        assert data["documents"][0]["url"] == "https://zbmath.org/7192477"

    @pytest.mark.asyncio
    async def test_correct_api_params(self):
        from server import search_documents

        mock_response = _make_mock_http_response({"status": {"nr_total_results": 0}, "result": []})
        with patch("server.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            await search_documents("test query", results_per_page=5, page=2)

        call_kwargs = mock_client.get.call_args
        assert call_kwargs[0][0] == "https://api.zbmath.org/v1/document/_search"
        params = call_kwargs[1]["params"]
        assert params["search_string"] == "test query"
        assert params["results_per_page"] == 5
        assert params["page"] == 2

    @pytest.mark.asyncio
    async def test_clamps_results_per_page(self):
        from server import search_documents

        mock_response = _make_mock_http_response({"status": {"nr_total_results": 0}, "result": []})
        with patch("server.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            await search_documents("test", results_per_page=200)

        params = mock_client.get.call_args[1]["params"]
        assert params["results_per_page"] == 100

    @pytest.mark.asyncio
    async def test_empty_results(self):
        from server import search_documents

        mock_response = _make_mock_http_response({"status": {"nr_total_results": 0}, "result": []})
        with patch("server.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await search_documents("xyzabcnonexistent")

        data = json.loads(result)
        assert data["total_results"] == 0
        assert data["documents"] == []

    @pytest.mark.asyncio
    async def test_second_doc_missing_review(self):
        from server import search_documents

        mock_response = _make_mock_http_response(MOCK_SEARCH_RESPONSE)
        with patch("server.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await search_documents("spectral theory")

        data = json.loads(result)
        assert data["documents"][1]["review"] == ""


    @pytest.mark.asyncio
    async def test_zero_results_404_is_not_an_error(self):
        """A no-match query returns HTTP 404; it must yield an empty result,
        not raise."""
        from server import search_documents

        mock_response = _make_mock_http_response(MOCK_ZERO_RESULTS_RESPONSE, status_code=404)
        # raise_for_status would normally raise on 404; make sure it isn't reached.
        mock_response.raise_for_status = MagicMock(side_effect=AssertionError("should not raise"))
        with patch("server.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await search_documents("zzzznomatchqueryzzzz")

        data = json.loads(result)
        assert data["total_results"] == 0
        assert data["documents"] == []


# ---------------------------------------------------------------------------
# Tests for get_document
# ---------------------------------------------------------------------------

class TestGetDocument:
    @pytest.mark.asyncio
    async def test_returns_document(self):
        from server import get_document

        mock_response = _make_mock_http_response(MOCK_DOCUMENT_RESPONSE)
        with patch("server.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_document(7192477)

        data = json.loads(result)
        assert data["id"] == 7192477
        assert data["year"] == 2020

    @pytest.mark.asyncio
    async def test_calls_correct_url(self):
        from server import get_document

        mock_response = _make_mock_http_response(MOCK_DOCUMENT_RESPONSE)
        with patch("server.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            await get_document(7192477)

        url = mock_client.get.call_args[0][0]
        assert url == "https://api.zbmath.org/v1/document/7192477"


# ---------------------------------------------------------------------------
# Tests for structured_search
# ---------------------------------------------------------------------------

class TestStructuredSearch:
    @pytest.mark.asyncio
    async def test_sends_author_param(self):
        from server import structured_search

        mock_response = _make_mock_http_response({"status": {"nr_total_results": 0}, "result": []})
        with patch("server.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            await structured_search(author="Euler")

        params = mock_client.get.call_args[1]["params"]
        assert params["Author name"] == "Euler"
        assert "Contributor name" not in params

    @pytest.mark.asyncio
    async def test_sends_msc_param(self):
        from server import structured_search

        mock_response = _make_mock_http_response({"status": {"nr_total_results": 0}, "result": []})
        with patch("server.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            await structured_search(msc_code="11M26")

        params = mock_client.get.call_args[1]["params"]
        assert params["MSC"] == "11M26"

    @pytest.mark.asyncio
    async def test_year_range_params(self):
        from server import structured_search

        mock_response = _make_mock_http_response({"status": {"nr_total_results": 0}, "result": []})
        with patch("server.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            await structured_search(year_from=2000, year_to=2010)

        params = mock_client.get.call_args[1]["params"]
        assert params["Year"] == "2000-2010"

    @pytest.mark.asyncio
    async def test_open_ended_year_ranges(self):
        from server import structured_search

        for kwargs, expected in [
            ({"year_from": 2000}, "2000-"),
            ({"year_to": 2010}, "-2010"),
            ({"year_from": 1999, "year_to": 1999}, "1999"),
        ]:
            mock_response = _make_mock_http_response({"status": {"nr_total_results": 0}, "result": []})
            with patch("server.httpx.AsyncClient") as MockClient:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

                await structured_search(**kwargs)

            params = mock_client.get.call_args[1]["params"]
            assert params["Year"] == expected

    @pytest.mark.asyncio
    async def test_omits_empty_params(self):
        from server import structured_search

        mock_response = _make_mock_http_response({"status": {"nr_total_results": 0}, "result": []})
        with patch("server.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            await structured_search()

        params = mock_client.get.call_args[1]["params"]
        for key in ("Author name", "Contributor name", "Title", "MSC", "Source", "Year"):
            assert key not in params


# ---------------------------------------------------------------------------
# Tests for get_author
# ---------------------------------------------------------------------------

class TestGetAuthor:
    @pytest.mark.asyncio
    async def test_returns_author(self):
        from server import get_author

        mock_response = _make_mock_http_response(MOCK_AUTHOR_RESPONSE)
        with patch("server.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_author("euler.leonhard")

        data = json.loads(result)
        assert data["id"] == "euler.leonhard"
        assert data["name"] == "Euler, Leonhard"

    @pytest.mark.asyncio
    async def test_calls_correct_url(self):
        from server import get_author

        mock_response = _make_mock_http_response(MOCK_AUTHOR_RESPONSE)
        with patch("server.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            await get_author("euler.leonhard")

        url = mock_client.get.call_args[0][0]
        assert url == "https://api.zbmath.org/v1/author/euler.leonhard"


# ---------------------------------------------------------------------------
# Tests for get_software
# ---------------------------------------------------------------------------

class TestGetSoftware:
    @pytest.mark.asyncio
    async def test_returns_software(self):
        from server import get_software

        mock_response = _make_mock_http_response(MOCK_SOFTWARE_RESPONSE)
        with patch("server.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_software(825)

        data = json.loads(result)
        assert data["id"] == 825
        assert data["name"] == "Macaulay2"

    @pytest.mark.asyncio
    async def test_calls_correct_url(self):
        from server import get_software

        mock_response = _make_mock_http_response(MOCK_SOFTWARE_RESPONSE)
        with patch("server.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            await get_software(825)

        url = mock_client.get.call_args[0][0]
        assert url == "https://api.zbmath.org/v1/software/825"
