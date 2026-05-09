import asyncio
from playwright.async_api import async_playwright
from .base import BaseProvider


class CopilotProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "copilot"

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=self._get_user_data_dir(),
            headless=self.headless,
        )
        self.page = await self.browser.new_page()
        await self.page.goto("https://copilot.microsoft.com/")
        await self.page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(3)

    async def send_message(self, message: str) -> str:
        # Find the input field
        input_selector = 'textarea'
        try:
            await self.page.wait_for_selector(input_selector, timeout=5000)
        except:
            pass

        textareas = await self.page.query_selector_all(input_selector)
        if not textareas:
            return "No input field found"

        await textareas[0].fill(message)
        await self.page.keyboard.press("Enter")

        # Wait for response
        response_selector = 'div[class*="response"]'
        await asyncio.sleep(0.5)

        # Wait for stability
        previous_text = ""
        stable_count = 0

        for _ in range(120):
            try:
                result = await self.page.evaluate("document.body.innerText")
                if result == previous_text:
                    stable_count += 1
                    if stable_count >= 3:
                        break
                else:
                    stable_count = 0
                previous_text = result
            except:
                pass
            await asyncio.sleep(0.2)

        try:
            content = await self.page.content()
            # Extract last substantial text block
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, "html.parser")
            # Find the response content
            for div in reversed(soup.find_all("div")):
                text = div.get_text(strip=True)
                if len(text) > 50:
                    return text[:2000]
        except:
            pass

        return "No response received"

    async def close(self):
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
