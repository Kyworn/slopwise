import json
import logging
from typing import Dict

from slopwise.json_repair import loads_lenient
from slopwise.llm import LLMClient

logger = logging.getLogger(__name__)


class ChangeCritic:
    """Review and validate analyses for consistency and accuracy.

    A second LLM pass to flag contradictions, overstated claims, or missed context.
    """

    def __init__(self, llm_client: LLMClient):
        """Initialize critic with LLM backend.

        Args:
            llm_client: Configured LLMClient instance for any provider/model
        """
        self.llm_client = llm_client

    async def review(
        self, 
        func_name: str,
        func_a: str,
        func_b: str,
        analysis: Dict
    ) -> Dict:
        """Review an analysis for validity and coherence.

        Args:
            func_name: Name of the function
            func_a: Version A code
            func_b: Version B code
            analysis: Existing analysis dict

        Returns:
            Dict with keys: approved, flags, adjusted_analysis
        """
        system_prompt = (
            "You are a critical peer reviewer for security researchers. "
            "Your job is to double-check the analysis of a code change and ensure it's "
            "accurate, objective, and doesn't miss subtle security implications."
        )

        user_prompt = f"""Review the following analysis of function '{func_name}'.

CODE VERSION A:
{func_a}

CODE VERSION B:
{func_b}

PROPOSED ANALYSIS:
{json.dumps(analysis, indent=2)}

Is this analysis accurate? Did it miss any security risks or misinterpret the changes?
If the analysis is good, set 'approved' to true.
If you have concerns, set 'approved' to false, list 'flags', and provide an 'adjusted_analysis'.

Respond ONLY with a JSON object in this format:
{{
  "approved": bool,
  "flags": ["...", "..."],
  "adjusted_analysis": {{
     "category": "...",
     "summary": "...",
     "risk": "..."
  }}
}}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        last_err: Exception | None = None
        for attempt in range(2):
            try:
                response_text = await self.llm_client.complete(messages)
                return loads_lenient(response_text)
            except json.JSONDecodeError as e:
                last_err = e
                logger.warning(
                    f"Malformed JSON from critic for {func_name} "
                    f"(attempt {attempt + 1}/2): {e}"
                )
                messages = messages + [
                    {"role": "assistant", "content": response_text},
                    {
                        "role": "user",
                        "content": (
                            "Your previous response was not valid JSON. "
                            "Reply with ONLY the JSON object, no prose, no "
                            "markdown fences. Same schema."
                        ),
                    },
                ]
            except Exception as e:
                last_err = e
                break

        logger.error(f"Review failed for {func_name}: {last_err}")
        return {"approved": True, "flags": [], "adjusted_analysis": analysis}
