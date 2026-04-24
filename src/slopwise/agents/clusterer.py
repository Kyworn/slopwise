import json
import logging
from typing import Dict, List

from slopwise.llm import LLMClient

logger = logging.getLogger(__name__)


class ChangeClusterer:
    """Group analyzed changes into semantic clusters.

    Uses an LLM to identify themes (e.g., "all crypto updates", "all bounds checks")
    and organize per-function analyses into coherent narrative categories.
    """

    def __init__(self, llm_client: LLMClient):
        """Initialize clusterer with LLM backend.

        Args:
            llm_client: Configured LLMClient instance for any provider/model
        """
        self.llm_client = llm_client

    async def cluster(self, analyses: List[Dict]) -> Dict[str, List[str]]:
        """Group function analyses by semantic theme.

        Args:
            analyses: List of analysis dicts from FunctionAnalyzer

        Returns:
            Dict mapping theme name -> list of function names in that cluster
        """
        if not analyses:
            return {}

        system_prompt = (
            "You are a technical lead overseeing a binary diffing project. "
            "Your goal is to group individual function changes into high-level 'themes' "
            "to make the report readable for humans."
        )
        
        # Prepare a condensed list for the prompt to save tokens
        condensed = [
            {"name": a["name"], "category": a["category"], "summary": a["summary"]}
            for r in [analyses] for a in r # Handle potential nesting if needed
        ]
        # Actually analyses is already a list of dicts
        condensed = [{"name": a["name"], "summary": a["summary"]} for a in analyses]

        user_prompt = f"""Below is a list of functions that changed between two versions of a binary, with a brief summary of each change.
Group these functions into 3 to 7 high-level themes (e.g., 'Memory Management', 'Network Protocol Update', 'Input Validation').

FUNCTIONS:
{json.dumps(condensed, indent=2)}

Respond ONLY with a JSON object where keys are theme names and values are lists of function names.
Example:
{{
  "Theme Name": ["func1", "func2"],
  "Another Theme": ["func3"]
}}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response_text = await self.llm_client.complete(messages)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            return json.loads(response_text)
        except Exception as e:
            logger.error(f"Clustering failed: {e}")
            return {"Miscellaneous": [a["name"] for a in analyses]}
