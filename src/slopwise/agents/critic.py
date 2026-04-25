"""Peer-review agent that audits the analyzer's output."""

import json
import logging

from pydantic import ValidationError

from slopwise.agents.schemas import CATEGORIES, RISKS, CriticResult
from slopwise.diff import canonicalize_for_llm
from slopwise.json_repair import loads_lenient
from slopwise.llm import LLMClient

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "You are a critical peer reviewer for security researchers. You audit "
    "an existing analysis of a code change for accuracy.\n"
    "\n"
    "RULES FOR RAISING FLAGS:\n"
    "- Every flag must cite a concrete token, line, or pattern from the "
    "diff that motivates it. If you cannot quote specific evidence, do NOT "
    "raise the flag.\n"
    "- 'incomplete_analysis', 'missing_security_implication', and similar "
    "vague flags are FORBIDDEN unless paired with a specific line citation.\n"
    "- Default to approving the analysis when it is correct, even if it is "
    "terse. Brevity is not a flaw.\n"
    "- Only set `approved=false` and provide an `adjusted_analysis` when "
    "the original analysis is wrong, not merely incomplete."
)


class ChangeCritic:
    """Audit an `AnalysisResult` for accuracy.

    Returns a `CriticResult` dict. When `approved` is true the caller keeps
    the original analysis; otherwise the caller substitutes
    `adjusted_analysis`.
    """

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    async def review(
        self,
        func_name: str,
        func_a: str,
        func_b: str,
        analysis: dict,
    ) -> dict:
        func_a, func_b = canonicalize_for_llm(func_a, func_b)
        user_prompt = self._build_prompt(func_name, func_a, func_b, analysis)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        last_err: Exception | None = None
        response_text = ""
        for attempt in range(2):
            try:
                response_text = await self.llm_client.complete(messages)
                raw = loads_lenient(response_text)
                return CriticResult.model_validate(raw).model_dump()
            except (json.JSONDecodeError, ValidationError) as e:
                last_err = e
                logger.warning(
                    "Critic schema/JSON failure for %s (attempt %d/2): %s",
                    func_name,
                    attempt + 1,
                    e,
                )
                messages = messages + [
                    {"role": "assistant", "content": response_text},
                    {"role": "user", "content": self._retry_nudge(e)},
                ]
            except Exception as e:
                last_err = e
                break

        logger.error("Review failed for %s: %s", func_name, last_err)
        # Fall through: keep the original analysis untouched.
        return CriticResult(
            approved=True, flags=[], adjusted_analysis=None
        ).model_dump()

    @staticmethod
    def _build_prompt(
        func_name: str, func_a: str, func_b: str, analysis: dict
    ) -> str:
        cats = ", ".join(CATEGORIES)
        risks = ", ".join(RISKS)
        return (
            f"Review the analysis of function '{func_name}'.\n\n"
            "CODE VERSION A:\n```c\n"
            f"{func_a}\n```\n\n"
            "CODE VERSION B:\n```c\n"
            f"{func_b}\n```\n\n"
            "PROPOSED ANALYSIS:\n"
            f"{json.dumps(analysis, indent=2)}\n\n"
            "Respond ONLY with a JSON object, no prose, no markdown fences:\n"
            "{\n"
            '  "approved": true | false,\n'
            '  "flags":    list of evidence-backed strings (may be empty),\n'
            '  "adjusted_analysis": null when approved=true; otherwise an '
            "object with the same schema as the proposed analysis "
            f"(category in [{cats}], risk in [{risks}], summary, details)\n"
            "}"
        )

    @staticmethod
    def _retry_nudge(err: Exception) -> str:
        return (
            "Your previous response did not match the required schema:\n"
            f"{err}\n\n"
            "Reply again with ONLY the JSON object -- keys: approved, flags, "
            "adjusted_analysis. No prose, no markdown fences."
        )
