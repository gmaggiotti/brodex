import asyncio
from playwright.async_api import async_playwright
from .base import BaseProvider


class HuggingChatProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "huggingchat"

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=self._get_user_data_dir(),
            headless=self.headless,
        )
        self.page = await self.browser.new_page()
        await self.page.goto("https://huggingface.co/chat/")
        await self.page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(3)

    async def send_message(self, message: str) -> str:
        # Find the input field
        input_selector = 'textarea[placeholder="Ask anything"]'
        try:
            await self.page.wait_for_selector(input_selector, timeout=5000)
        except:
            # Try alternative selector
            input_selector = 'textarea'

        textareas = await self.page.query_selector_all(input_selector)
        if not textareas:
            return "No input field found"

        await textareas[0].fill(message)

        # Send message
        button_selector = 'button[aria-label="Send"]'
        buttons = await self.page.query_selector_all(button_selector)
        if buttons:
            await buttons[0].click()
        else:
            await self.page.keyboard.press("Enter")

        # Wait for response
        await asyncio.sleep(1)

        # Wait for stability
        previous_text = ""
        stable_count = 0

        for _ in range(120):
            try:
                # Get the last message from the assistant
                result = await self.page.evaluate(
                    """
                    () => {
                        const messages = document.querySelectorAll('[class*="message"]');
                        if (messages.length > 0) {
                            return messages[messages.length - 1].innerText;
                        }
                        return '';
                    }
                    """
                )
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
            result = await self.page.evaluate(
                """
                () => {
                    const messages = document.querySelectorAll('[class*="message"]');
                    if (messages.length > 0) {
                        return messages[messages.length - 1].innerText;
                    }
                    return '';
                }
                """
            )
            if result:
                return result
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
