import httpx
from bs4 import BeautifulSoup


async def search_web(query: str) -> str:
    """Search the web using DuckDuckGo and return top results."""
    try:
        url = "https://duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

        results = []
        for result in data.get("Results", [])[:5]:
            title = result.get("Title", "")
            url = result.get("FirstURL", "")
            snippet = result.get("Text", "")
            if title and url:
                results.append(f"**{title}**\n{url}\n{snippet}\n")

        if results:
            return "## Search Results\n\n" + "\n".join(results)
        return "No search results found"
    except Exception as e:
        return f"Error searching web: {e}"
