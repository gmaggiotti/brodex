import os
from groq import Groq


class GroqProvider:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY environment variable not set. "
                "Get it from https://console.groq.com"
            )
        self.client = Groq(api_key=api_key)
        self.model = "qwen/qwen3-32b"
        self.messages = []

    async def send_message(self, message: str) -> str:
        """Send message to Groq and get response."""
        self.messages.append({"role": "user", "content": message})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                temperature=0.7,
                max_tokens=2048,
            )
            assistant_message = response.choices[0].message.content
            self.messages.append({"role": "assistant", "content": assistant_message})
            return assistant_message
        except Exception as e:
            return f"Error: {e}"

    def clear_history(self):
        """Clear conversation history."""
        self.messages = []

    def get_models(self):
        """List available models."""
        return [
            "llama-3.1-70b-versatile",   # Most capable
            "llama-3.1-8b-instant",      # Fast, lightweight
            "gemma-2-9b-it",             # Good balance
        ]
