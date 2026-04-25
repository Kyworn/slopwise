"""LiteLLM wrapper for provider-agnostic LLM access."""

import asyncio
import logging

import litellm
from .config import AgentConfig

logger = logging.getLogger(__name__)


class LLMClient:
    """Unified LLM client supporting any backend via LiteLLM.

    Supports: Claude, GPT-4, Gemini, Ollama, vLLM, OpenRouter, local inference, etc.
    Plus a `gemini_cli` provider that shells out to the `gemini` CLI for users
    on Google account auth (no API key).
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
        if self.provider and self.provider.lower() == "gemini_cli":
            return await self._complete_gemini_cli(messages)

        response = await litellm.acompletion(
            model=self._model_str,
            messages=messages,
            api_key=self.api_key,
            api_base=self.base_url,
        )
        return response.choices[0].message.content

    async def _complete_gemini_cli(self, messages: list[dict]) -> str:
        """Invoke the `gemini` CLI in headless mode.

        Uses Google-account auth -- no API key. Prompt is fed via stdin to
        avoid argv length limits on long decompiled functions.
        """
        # Flatten chat messages into a single prompt. The CLI is single-turn,
        # so we prefix system messages and merge user/assistant turns.
        parts: list[str] = []
        for m in messages:
            role = m.get("role", "user").upper()
            parts.append(f"[{role}]\n{m['content']}")
        prompt = "\n\n".join(parts)

        cmd = ["gemini", "-p", prompt, "-o", "text"]
        if self.model:
            cmd += ["-m", self.model]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(
                f"gemini CLI exited {proc.returncode}: "
                f"{stderr.decode(errors='replace').strip()}"
            )
        return stdout.decode(errors="replace").strip()
