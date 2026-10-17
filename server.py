"""zbMath MCP server — exposes zbMath Open REST API as MCP tools."""

from __future__ import annotations

import json
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

ZBMATH_API_BASE = "https://api.zbmath.org/v1"

mcp = FastMCP(
    "zbmath",
    instructions=(
        "Tools for searching and retrieving mathematical literature from "
        "zbMath Open (https://zbmath.org), the world's most comprehensive "
        "database for mathematical publications."
    ),
)


async def _get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Send a GET request to the zbMath API and return the parsed JSON.

    The zbMath API answers a well-formed query that simply has no matches
    with HTTP 404 and a body whose status reads "Zero results". We treat that
    as an empty (not failed) response and return the body unchanged; any other
    error status is raised.
    """
    url = f"{ZBMATH_API_BASE}{path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        if response.status_code == 404:
            try:
                body = response.json()
            except ValueError:
                body = None
            if isinstance(body, dict) and "status" in body:
                return body
        response.raise_for_status()
        return response.json()


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def _summarize_document(doc: dict[str, Any]) -> dict[str, Any]:
    """Reduce a raw zbMath document record to a compact summary.

    Maps the fields of the zbMath Open REST API response (verified against the
    live API) to a flat, assistant-friendly shape.
    """
    title_field = doc.get("title") or {}
    title = (
        title_field.get("title", "")
        if isinstance(title_field, dict)
        else str(title_field)
    )

    contributors = doc.get("contributors") or {}
    authors = [a.get("name", "") for a in contributors.get("authors", [])]

    # The journal/series lives under source.series (a list); source.source is
    # the human-readable bibliographic citation string.
    source = doc.get("source") or {}
    series = source.get("series") or []
    journal = ""
    if isinstance(series, list) and series:
        journal = series[0].get("title", "")
    elif isinstance(series, dict):
        journal = series.get("title", "")

    # MSC codes are a top-level "msc" list of {code, scheme, text} objects.
    msc_codes = [m.get("code", "") for m in doc.get("msc") or []]

    # "keywords" is a flat list of strings.
    keywords = [k for k in doc.get("keywords") or [] if isinstance(k, str)]

    reviews = doc.get("editorial_contributions") or []
    review_text = reviews[0].get("text", "") if reviews else ""

    return {
        "zbmath_id": doc.get("id"),
        "title": title,
        "authors": authors,
        "year": doc.get("year"),
        "journal": journal,
        "source": source.get("source", ""),
        "msc_codes": msc_codes,
        "keywords": keywords,
        "review": review_text[:400] if review_text else "",
        "url": doc.get("zbmath_url") or f"https://zbmath.org/{doc.get('id')}",
    }


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def search_documents(
    query: str,
    results_per_page: int = 10,
    page: int = 0,
) -> str:
    """Search zbMath Open for mathematical documents using a free-text query.

    Args:
        query: Free-text search string, e.g. "Riemann hypothesis" or
               "spectral theory elliptic operators".
        results_per_page: Number of results to return (1–100, default 10).
        page: Zero-based page index for pagination (default 0).

    Returns:
        JSON string containing total result count and a list of matching
        documents, each with id, title, authors, year, journal, MSC codes,
        a short review excerpt, and a zbMath URL.
    """
    results_per_page = max(1, min(results_per_page, 100))
    data = await _get(
        "/document/_search",
        params={
            "search_string": query,
            "page": page,
            "results_per_page": results_per_page,
        },
    )

    total = data.get("status", {}).get("nr_total_results") or 0
    documents = [_summarize_document(doc) for doc in (data.get("result") or [])]

    return json.dumps(
        {"total_results": total, "page": page, "documents": documents},
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
async def get_document(zbmath_id: int) -> str:
    """Retrieve full metadata for a single zbMath document by its numeric ID.

    Args:
        zbmath_id: The numeric zbMath document identifier
                   (e.g. 7192477 for Zbl 7192477).

    Returns:
        JSON string with complete document metadata including title, authors,
        abstract, MSC classification, journal, DOI, review, and links.
    """
    data = await _get(f"/document/{zbmath_id}")
    result = data.get("result") or {}
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def structured_search(
    author: str = "",
    title: str = "",
    msc_code: str = "",
    year_from: int | None = None,
    year_to: int | None = None,
    journal: str = "",
    results_per_page: int = 10,
    page: int = 0,
) -> str:
    """Search zbMath documents using structured field filters.

    Use this instead of search_documents when you want to restrict results
    to specific fields such as author name, MSC subject class, or year range.

    Args:
        author: Author (contributor) name, e.g. "Euler" or "Riemann, B.".
        title: Words or phrases to match in the document title.
        msc_code: MSC 2020 classification code, e.g. "11" for Number Theory
                  or "35J15" for a specific code.
        year_from: Earliest publication year (inclusive).
        year_to:   Latest publication year (inclusive).
        journal: Journal / bibliographic source name fragment.
        results_per_page: Number of results (1–100, default 10).
        page: Zero-based page index for pagination (default 0).

    Returns:
        JSON string with total result count and matching documents.
    """
    results_per_page = max(1, min(results_per_page, 100))
    # The zbMath structured-search endpoint uses human-readable field names
    # (verified against the live API / OpenAPI spec), not short codes.
    params: dict[str, Any] = {
        "page": page,
        "results_per_page": results_per_page,
    }
    if author:
        params["Author name"] = author
    if title:
        params["Title"] = title
    if msc_code:
        params["MSC"] = msc_code
    if journal:
        params["Source"] = journal

    # The "Year" field takes a single value or an interval "from-to";
    # an open-ended interval is "from-" or "-to".
    if year_from is not None and year_to is not None:
        params["Year"] = (
            str(year_from)
            if year_from == year_to
            else f"{year_from}-{year_to}"
        )
    elif year_from is not None:
        params["Year"] = f"{year_from}-"
    elif year_to is not None:
        params["Year"] = f"-{year_to}"

    data = await _get("/document/_structured_search", params=params)

    total = data.get("status", {}).get("nr_total_results") or 0
    documents = [_summarize_document(doc) for doc in (data.get("result") or [])]

    return json.dumps(
        {"total_results": total, "page": page, "documents": documents},
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
async def get_author(author_id: str) -> str:
    """Retrieve profile information for a zbMath author by their profile ID.

    Args:
        author_id: The zbMath author profile identifier string,
                   e.g. "euler.leonhard" or "gauss.carl-friedrich".

    Returns:
        JSON string with the author's profile data including name variants,
        affiliated institutions, and publication count.
    """
    data = await _get(f"/author/{author_id}")
    result = data.get("result") or {}
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def get_software(software_id: int) -> str:
    """Retrieve metadata for a zbMath / swMath software entry by its numeric ID.

    Args:
        software_id: The numeric swMath software identifier.

    Returns:
        JSON string with software metadata including name, description,
        programming language, keywords, and references.
    """
    data = await _get(f"/software/{software_id}")
    result = data.get("result") or {}
    return json.dumps(result, ensure_ascii=False, indent=2)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
