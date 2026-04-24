import json
import logging
from typing import Dict

from slopwise.llm import LLMClient

logger = logging.getLogger(__name__)


class FunctionAnalyzer:
    """Analyze semantic changes in individual functions via LLM.

    Prompts the LLM to classify each change (bugfix, feature, refactor, security)
    and provide a human-readable summary and risk assessment.
    """

    def __init__(self, llm_client: LLMClient):
        """Initialize analyzer with LLM backend.

        Args:
            llm_client: Configured LLMClient instance for any provider/model
        """
        self.llm_client = llm_client

    async def analyze(
        self, 
        func_name: str,
        func_a_decompile: str, 
        func_b_decompile: str
    ) -> Dict:
        """Analyze difference between two function versions.

        Args:
            func_name: Name of the function being analyzed
            func_a_decompile: Decompiled pseudocode from version A
            func_b_decompile: Decompiled pseudocode from version B

        Returns:
            Dict with keys: category, summary, risk, details
        """
        # Point 2: Token Management
        # Approximate limit of 15000 characters per function version to stay safe
        MAX_CHARS = 15000
        
        def truncate(code):
            if len(code) > MAX_CHARS:
                return code[:MAX_CHARS] + "\n/* ... [TRUNCATED DUE TO SIZE] ... */"
            return code

        func_a = truncate(func_a_decompile)
        func_b = truncate(func_b_decompile)

        system_prompt = (
            "You are a senior security researcher and reverse engineer. "
            "Your task is to analyze changes between two versions of a decompiled C function "
            "and explain the semantic meaning of these changes."
        )
        
        user_prompt = f"""Analyze the changes in function '{func_name}'.

VERSION A:
```c
{func_a}
```

VERSION B:
```c
{func_b}
```

Provide a semantic analysis. Focus on the 'why' (e.g., 'added bounds check', 'optimized loop').
Categorize the change as one of: bugfix, feature, refactor, security, or other.
Assess risk as: low, medium, or high.

Respond ONLY with a JSON object in this format:
{{
  "category": "...",
  "summary": "...",
  "risk": "...",
  "details": "..."
}}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response_text = await self.llm_client.complete(messages)
            # Basic JSON extraction in case the LLM adds markdown blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            return json.loads(response_text)
        except Exception as e:
            logger.error(f"Analysis failed for {func_name}: {e}")
            return {
                "category": "error",
                "summary": f"Failed to analyze: {str(e)}",
                "risk": "unknown",
                "details": ""
            }
