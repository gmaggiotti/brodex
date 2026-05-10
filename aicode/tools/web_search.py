from urllib.parse import parse_qs, unquote, urlparse

import httpx
from bs4 import BeautifulSoup


# DuckDuckGo's `/?format=json` endpoint is the *Instant Answer* API — it only
# returns data for queries with a curated answer (Wikipedia-style summaries,
# calculator results, etc.). For ordinary searches it returns empty fields
# even when the public web has plenty of pages. The HTML endpoint below
# returns real organic results without an API key.
_HTML_URL = "https://html.duckduckgo.com/html/"
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}


def _unwrap_ddg_link(href: str) -> str:
    """DDG wraps some result links as `//duckduckgo.com/l/?uddg=<encoded url>`."""
    if not href:
        return href
    parsed = urlparse(href if href.startswith("http") else f"https:{href}")
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
        target = parse_qs(parsed.query).get("uddg", [None])[0]
        if target:
            return unquote(target)
    return href


async def search_web(query: str) -> str:
    """Search the web via DuckDuckGo's HTML endpoint and return top results."""
    try:
        async with httpx.AsyncClient(
            headers=_BROWSER_HEADERS, follow_redirects=True
        ) as client:
            response = await client.post(
                _HTML_URL, data={"q": query}, timeout=10
            )
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        results = []
        for node in soup.select("div.result")[:5]:
            link = node.select_one("a.result__a")
            snippet = node.select_one(".result__snippet")
            if not link:
                continue
            title = link.get_text(strip=True)
            url = _unwrap_ddg_link(link.get("href", ""))
            text = snippet.get_text(strip=True) if snippet else ""
            if title and url:
                results.append(f"**{title}**\n{url}\n{text}\n")

        if results:
            return "## Search Results\n\n" + "\n".join(results)
        return "No search results found"
    except Exception as e:
        return f"Error searching web: {e}"
