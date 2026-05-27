"""MCP tools: web_search (Tavily) and scrape_url (httpx + bs4)."""

from __future__ import annotations

import logging

from bs4 import BeautifulSoup
from fastmcp import FastMCP

from forgeflow.config import get_settings

logger = logging.getLogger(__name__)

router = FastMCP("search-tools")


@router.tool()
async def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web for recent information about a company or topic.

    Args:
        query: Natural-language search query
        max_results: Number of results to return (1-10)

    Returns:
        List of {title, url, content, score} dicts from Tavily
    """
    settings = get_settings()

    if not settings.is_tavily_enabled():
        # Mock results for development without a Tavily key
        logger.warning("Tavily not configured — returning mock search results")
        return [
            {
                "title": f"Mock result for: {query}",
                "url": "https://example.com/mock",
                "content": f"This is mock search content for query: {query}. "
                "The company has approximately 500 employees and raised $50M Series B.",
                "score": 0.85,
            }
        ]

    try:
        from tavily import AsyncTavilyClient

        client = AsyncTavilyClient(api_key=settings.tavily_api_key.get_secret_value())
        response = await client.search(
            query=query,
            max_results=min(max_results, 10),
            search_depth="basic",
            include_raw_content=False,
        )
        return response.get("results", [])
    except Exception as e:
        logger.error("Tavily search failed: %s", e)
        return [{"error": str(e), "query": query}]


@router.tool()
async def scrape_url(url: str) -> str:
    """Fetch and extract clean text content from a URL.

    SSRF-hardened: rejects private/loopback/link-local hosts (incl. IMDS),
    non-HTTP schemes, userinfo URLs, and re-validates every redirect.
    See forgeflow/security/ssrf_guard.py.

    Args:
        url: Fully-qualified public URL to fetch
    Returns:
        Cleaned plain text (up to 5000 chars), or an error message.
    """
    from forgeflow.security.ssrf_guard import SSRFBlocked, safe_get

    try:
        response = await safe_get(url)
        response.raise_for_status()
    except SSRFBlocked as e:
        logger.warning("SSRF-blocked scrape | url=%s reason=%s", url, e)
        return f"Refused to fetch {url}: {e}"
    except Exception as e:
        logger.error("URL scrape failed for %s: %s", url, e)
        return f"Error fetching {url}: {e}"

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)[:5000]
