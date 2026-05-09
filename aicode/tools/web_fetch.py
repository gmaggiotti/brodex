import httpx
from bs4 import BeautifulSoup


async def fetch_url(url: str) -> str:
    """Fetch URL content and extract main text."""
    try:
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text
        text = soup.get_text()

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = "\n".join(chunk for chunk in chunks if chunk)

        # Limit to first 2000 characters
        text = text[:2000]

        return f"## Content from {url}\n\n```\n{text}\n```"
    except Exception as e:
        return f"Error fetching URL: {e}"
