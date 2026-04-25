"""Best-effort JSON extraction from messy LLM outputs."""

import json
import re
from typing import Any


_FENCE_JSON = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _extract_balanced_object(text: str) -> str | None:
    """Return the first balanced `{...}` block, ignoring braces inside strings."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def loads_lenient(text: str) -> Any:
    """Parse JSON from an LLM response that may contain markdown fences,
    leading/trailing prose, trailing commas, or premature truncation.

    Raises `json.JSONDecodeError` if no salvageable object can be found.
    """
    fence = _FENCE_JSON.search(text)
    if fence:
        text = fence.group(1)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    obj = _extract_balanced_object(text)
    if obj is None:
        raise json.JSONDecodeError("no `{...}` block found", text, 0)

    try:
        return json.loads(obj)
    except json.JSONDecodeError:
        # Strip trailing commas before } or ]
        cleaned = re.sub(r",(\s*[}\]])", r"\1", obj)
        return json.loads(cleaned)
