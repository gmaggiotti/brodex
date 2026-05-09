import os
from groq import Groq


# Approximate free-tier tokens-per-minute limits per model on Groq.
# Used to scale max_tokens and trim history so requests fit the per-call budget.
MODEL_TPM = {
    "allam-2-7b": 6000,
    "groq/compound": 70000,
    "groq/compound-mini": 70000,
    "llama-3.1-8b-instant": 6000,
    "llama-3.3-70b-versatile": 12000,
    "meta-llama/llama-4-scout-17b-16e-instruct": 30000,
    "meta-llama/llama-prompt-guard-2-22m": 15000,
    "meta-llama/llama-prompt-guard-2-86m": 15000,
    "openai/gpt-oss-120b": 8000,
    "openai/gpt-oss-20b": 8000,
    "openai/gpt-oss-safeguard-20b": 8000,
    "qwen/qwen3-32b": 6000,
}
DEFAULT_TPM = 6000


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

        tpm = MODEL_TPM.get(self.model, DEFAULT_TPM)
        max_output = max(512, min(2048, tpm // 4))
        # Reserve room for output and a safety margin so we don't hit the cap.
        input_budget = max(512, tpm - max_output - 256)

        messages_to_send = self._trim_to_budget(self.messages, input_budget)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages_to_send,
                temperature=0.7,
                max_tokens=max_output,
            )
            assistant_message = response.choices[0].message.content
            self.messages.append({"role": "assistant", "content": assistant_message})
            # Persist trimming so future calls don't re-blow the same budget.
            self.messages = self._trim_to_budget(self.messages, input_budget)
            return assistant_message
        except Exception as e:
            return self._format_error(e, tpm)

    def clear_history(self):
        """Clear conversation history."""
        self.messages = []

    def get_models(self):
        """List available models."""
        return list(MODEL_TPM.keys())

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        return max(1, len(text) // 4)

    @classmethod
    def _trim_to_budget(cls, messages: list, budget: int) -> list:
        """Drop oldest non-system messages until estimated tokens fit budget."""
        if not messages:
            return messages
        system_msgs = [m for m in messages if m.get("role") == "system"]
        other = [m for m in messages if m.get("role") != "system"]

        def total(msgs):
            return sum(cls._estimate_tokens(m.get("content", "")) for m in msgs)

        # Always keep at least the latest message; drop older ones first.
        while len(other) > 1 and total(system_msgs + other) > budget:
            other.pop(0)

        return system_msgs + other

    def _format_error(self, exc: Exception, tpm: int) -> str:
        text = str(exc)
        if "rate_limit_exceeded" in text or "Request too large" in text or "413" in text:
            higher = sorted(
                ((m, t) for m, t in MODEL_TPM.items() if t > tpm),
                key=lambda kv: -kv[1],
            )
            suggestion = ""
            if higher:
                names = ", ".join(m for m, _ in higher[:3])
                suggestion = f" Try a higher-capacity model (/model <name>): {names}."
            return (
                f"Error: request too large for `{self.model}` "
                f"(TPM limit: {tpm}).{suggestion} Or run /clear to reset history."
            )
        return f"Error: {exc}"
