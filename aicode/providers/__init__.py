from .base import BaseProvider
from .meta_ai import MetaAIProvider
from .chatgpt import ChatGPTProvider
from .copilot import CopilotProvider
from .huggingchat import HuggingChatProvider

PROVIDERS = {
    "meta": MetaAIProvider,
    "chatgpt": ChatGPTProvider,
    "copilot": CopilotProvider,
    "huggingchat": HuggingChatProvider,
}

__all__ = ["BaseProvider", "PROVIDERS"]
