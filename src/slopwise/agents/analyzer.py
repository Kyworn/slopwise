"""Per-function analyzer agent."""

import json
import logging

from pydantic import ValidationError

from slopwise.agents.schemas import CATEGORIES, RISKS, AnalysisResult
from slopwise.diff import canonicalize_for_llm
from slopwise.json_repair import loads_lenient
from slopwise.llm import LLMClient

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "You are a senior security researcher and reverse engineer. Your task "
    "is to analyze the difference between two decompiled C functions and "
    "explain the semantic meaning of the change.\n"
    "\n"
    "RISK CALIBRATION (be strict -- most changes are LOW):\n"
    "- HIGH:   exploitable bug reachable from untrusted input -- RCE, OOB "
    "write, auth bypass, leak of sensitive memory.\n"
    "- MEDIUM: bug with security implications but not directly exploitable "
    "-- NULL deref reachable from a public API, missing bounds check on a "
    "buffer that callers may control, logic error that corrupts state.\n"
    "- LOW:    refactor, version bump, robustness hardening, "
    "behavior-preserving cleanup, or any change with no plausible security "
    "impact.\n"
    "\n"
    "If unsure between two levels, pick the LOWER one."
)


class FunctionAnalyzer:
    """Classify and summarize the change between two function versions.

    Output is validated against `AnalysisResult`; on validation failure the
    LLM is given one chance to retry with the schema error spelled out.
    """

    MAX_CHARS = 15000  # ~3k tokens per version, well under context limits

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    async def analyze(
        self,
        func_name: str,
        func_a_decompile: str,
        func_b_decompile: str,
    ) -> dict:
        # Canonicalize Ghidra address artifacts so the model doesn't latch
        # onto `func_0xNNNN` shifts as evidence of a real change.
        func_a_canon, func_b_canon = canonicalize_for_llm(
            func_a_decompile, func_b_decompile
        )
        func_a = self._truncate(func_a_canon)
        func_b = self._truncate(func_b_canon)

        user_prompt = self._build_prompt(func_name, func_a, func_b)
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
                return AnalysisResult.model_validate(raw).model_dump()
            except (json.JSONDecodeError, ValidationError) as e:
                last_err = e
                logger.warning(
                    "Analyzer schema/JSON failure for %s (attempt %d/2): %s",
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

        logger.error("Analysis failed for %s: %s", func_name, last_err)
        return AnalysisResult(
            category="other",
            risk="low",
            summary=f"Failed to analyze: {last_err}",
            details="",
        ).model_dump()

    @classmethod
    def _truncate(cls, code: str) -> str:
        if len(code) > cls.MAX_CHARS:
            return code[: cls.MAX_CHARS] + "\n/* ... [TRUNCATED] ... */"
        return code

    @staticmethod
    def _build_prompt(func_name: str, func_a: str, func_b: str) -> str:
        cats = ", ".join(CATEGORIES)
        risks = ", ".join(RISKS)
        return (
            f"Analyze the changes in function '{func_name}'.\n\n"
            "VERSION A:\n```c\n"
            f"{func_a}\n```\n\n"
            "VERSION B:\n```c\n"
            f"{func_b}\n```\n\n"
            "Focus on the 'why' (e.g., 'added bounds check', "
            "'removed redundant null check').\n\n"
            "Respond ONLY with a JSON object, no prose, no markdown fences:\n"
            "{\n"
            f'  "category": one of [{cats}],\n'
            f'  "risk":     one of [{risks}],\n'
            '  "summary":  one-sentence headline,\n'
            '  "details":  optional longer explanation (may be empty)\n'
            "}"
        )

    @staticmethod
    def _retry_nudge(err: Exception) -> str:
        return (
            "Your previous response did not match the required schema:\n"
            f"{err}\n\n"
            "Reply again with ONLY the JSON object. `category` must be one "
            f"of [{', '.join(CATEGORIES)}]. `risk` must be one of "
            f"[{', '.join(RISKS)}]. No prose, no markdown fences."
        )
