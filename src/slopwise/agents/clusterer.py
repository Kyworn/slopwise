"""Theme-clustering agent that groups per-function analyses."""

import json
import logging

from pydantic import ValidationError

from slopwise.agents.schemas import ClusterResult
from slopwise.json_repair import loads_lenient
from slopwise.llm import LLMClient

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "You are a technical lead overseeing a binary diffing project. Group "
    "individual function changes into a small number of high-level themes "
    "to make the report scannable for humans."
)


class ChangeClusterer:
    """Group `AnalysisResult`-shaped dicts into named themes."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    async def cluster(self, analyses: list[dict]) -> dict[str, list[str]]:
        if not analyses:
            return {}

        condensed = [
            {"name": a["name"], "summary": a.get("summary", "")}
            for a in analyses
        ]
        names = {a["name"] for a in analyses}

        user_prompt = (
            "Below is a list of functions that changed between two binary "
            "versions, with a one-line summary of each change. Group them "
            "into 3 to 7 themes (e.g., 'Memory Management', 'Input "
            "Validation', 'Refactor').\n\n"
            "FUNCTIONS:\n"
            f"{json.dumps(condensed, indent=2)}\n\n"
            "Respond ONLY with a JSON object -- no prose, no markdown "
            "fences. Schema:\n"
            "{\n"
            '  "themes": {\n'
            '    "Theme Name": ["func1", "func2"],\n'
            '    "Another Theme": ["func3"]\n'
            "  }\n"
            "}"
        )

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
                # Tolerate either {"themes": {...}} (current schema) or a
                # bare {theme: [...]} mapping returned by older prompts.
                if "themes" not in raw and all(
                    isinstance(v, list) for v in raw.values()
                ):
                    raw = {"themes": raw}
                themes = ClusterResult.model_validate(raw).themes
                return self._ensure_complete(themes, names)
            except (json.JSONDecodeError, ValidationError) as e:
                last_err = e
                logger.warning(
                    "Clusterer schema/JSON failure (attempt %d/2): %s",
                    attempt + 1,
                    e,
                )
                messages = messages + [
                    {"role": "assistant", "content": response_text},
                    {
                        "role": "user",
                        "content": (
                            "Your previous response did not match the "
                            f"required schema:\n{e}\n\n"
                            'Reply with ONLY {"themes": {<name>: [<funcs>]}}.'
                        ),
                    },
                ]
            except Exception as e:
                last_err = e
                break

        logger.error("Clustering failed: %s", last_err)
        return {"Miscellaneous": [a["name"] for a in analyses]}

    @staticmethod
    def _ensure_complete(
        themes: dict[str, list[str]], expected: set[str]
    ) -> dict[str, list[str]]:
        """Drop unknown names and dump anything the model forgot into a
        catch-all bucket so every analyzed function appears exactly once
        in the report."""
        seen: set[str] = set()
        cleaned: dict[str, list[str]] = {}
        for theme, funcs in themes.items():
            kept = [f for f in funcs if f in expected and f not in seen]
            if kept:
                cleaned[theme] = kept
                seen.update(kept)
        missing = expected - seen
        if missing:
            cleaned.setdefault("Miscellaneous", []).extend(sorted(missing))
        return cleaned
