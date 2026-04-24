"""LiteLLM wrapper for provider-agnostic LLM access."""

import litellm
from typing import Optional
from .config import AgentConfig


class LLMClient:
    """Unified LLM client supporting any backend via LiteLLM.

    Supports: Claude, GPT-4, Gemini, Ollama, vLLM, OpenRouter, local inference, etc.
    Configuration driven via config.yaml provider/model/api_key settings.
    """

    def __init__(self, config: AgentConfig):
        """Initialize LLM client from config.

        Args:
            config: AgentConfig object containing provider, model, etc.
        """
        self.provider = config.provider
        self.model = config.model
        self.api_key = config.api_key
        self.base_url = config.base_url

        # Format model string for LiteLLM if provider prefix is missing
        # e.g., "claude-3..." -> "anthropic/claude-3..."
        self._model_str = self.model
        if self.provider and "/" not in self.model:
            # LiteLLM provider aliases
            provider_map = {
                "claude": "anthropic",
                "openai": "openai",
                "gemini": "gemini",
                "ollama": "ollama",
            }
            prefix = provider_map.get(self.provider.lower(), self.provider)
            self._model_str = f"{prefix}/{self.model}"

    async def complete(self, messages: list[dict]) -> str:
        """Generate completion from LLM.

        Args:
            messages: List of role/content dicts (OpenAI message format)

        Returns:
            Text response from LLM
        """
        response = await litellm.acompletion(
            model=self._model_str,
            messages=messages,
            api_key=self.api_key,
            api_base=self.base_url,
        )
        return response.choices[0].message.content
