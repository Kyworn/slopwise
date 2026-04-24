"""LiteLLM wrapper for provider-agnostic LLM access."""

import litellm
from typing import Optional


class LLMClient:
    """Unified LLM client supporting any backend via LiteLLM.

    Supports: Claude, GPT-4, Gemini, Ollama, vLLM, OpenRouter, local inference, etc.
    Configuration driven via config.yaml provider/model/api_key settings.
    """

    def __init__(
        self,
        provider: str,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """Initialize LLM client.

        Args:
            provider: Backend name (e.g., "claude", "openai", "ollama")
            model: Model identifier (e.g., "claude-3-5-sonnet-20241022")
            api_key: API key (env var expansion handled by config loader)
            base_url: Optional custom endpoint (for local/self-hosted inference)
        """
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

    async def complete(self, messages: list[dict]) -> str:
        """Generate completion from LLM.

        Args:
            messages: List of role/content dicts (OpenAI message format)

        Returns:
            Text response from LLM
        """
        raise NotImplementedError("LLMClient.complete() pending LiteLLM integration")
