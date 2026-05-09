import asyncio
from playwright.async_api import async_playwright
from .base import BaseProvider


class MetaAIProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "meta"

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=self._get_user_data_dir(),
            headless=self.headless,
        )
        self.page = await self.browser.new_page()
        await self.page.goto("https://www.meta.ai/")
        await self.page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)

    async def send_message(self, message: str) -> str:
        # Find the input field
        input_selector = 'textarea[placeholder="Ask me anything..."]'
        await self.page.fill(input_selector, message)

        # Submit
        await self.page.keyboard.press("Enter")

        # Wait for response to appear
        response_selector = 'div[data-testid="chat-message-text-stream"]'
        try:
            await self.page.wait_for_selector(response_selector, timeout=5000)
        except:
            pass

        # Wait for response to complete (text stability)
        await asyncio.sleep(0.5)
        previous_text = ""
        stable_count = 0

        for _ in range(60):
            try:
                elements = await self.page.query_selector_all(response_selector)
                if elements:
                    current_text = await elements[-1].inner_text()
                    if current_text == previous_text:
                        stable_count += 1
                        if stable_count >= 3:
                            break
                    else:
                        stable_count = 0
                    previous_text = current_text
            except:
                pass
            await asyncio.sleep(0.2)

        # Extract response
        try:
            elements = await self.page.query_selector_all(response_selector)
            if elements:
                return await elements[-1].inner_text()
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
