from abc import ABC, abstractmethod
from pathlib import Path


class BaseProvider(ABC):
    def __init__(self, headless=True):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None

    @abstractmethod
    async def start(self):
        """Launch browser and navigate to the AI chat interface."""
        pass

    @abstractmethod
    async def send_message(self, message: str) -> str:
        """Send message and return AI response."""
        pass

    @abstractmethod
    async def close(self):
        """Close browser and clean up resources."""
        pass

    def _get_user_data_dir(self) -> str:
        """Get persistent user data directory for browser context."""
        data_dir = Path.home() / ".aicode" / self.name
        data_dir.mkdir(parents=True, exist_ok=True)
        return str(data_dir)

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier."""
        pass
