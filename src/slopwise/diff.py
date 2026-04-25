"""Function matching and diffing logic with fuzzy matching support."""

import difflib
import re
from typing import Dict, List, Optional

from pydantic import BaseModel


_FUNC_REF_RE = re.compile(r"func_0x[0-9a-fA-F]+")
_LABEL_REF_RE = re.compile(r"code_r?0x[0-9a-fA-F]+")
_ADDR_RE = re.compile(r"\b0x[0-9a-fA-F]{4,}\b")
# Ghidra-synthesized local vars: auStack_38, pcStack_20, lStack_18, uStack_28...
# The numeric suffix is a stack offset that shifts whenever the frame layout
# changes (extra register save, alignment), so it's noise.
_STACK_VAR_RE = re.compile(r"\b([a-z]{1,4}Stack_)[0-9a-fA-F]+\b")
# Decompiler comments referencing absolute addresses (unreachable-block warnings,
# fallthrough notes, etc.) shift on every recompile.
_GHIDRA_COMMENT_RE = re.compile(r"^.*(WARNING|NOTE|INFO):.*0x[0-9a-fA-F]+.*$", re.MULTILINE)


def normalize_decompiled(code: str) -> str:
    """Strip Ghidra address artifacts that shift on every recompile.

    Replaces `func_0xNNNN` call targets, `code_r0xNNNN` jump labels, bare
    `0xNNNN` literals (>=4 hex digits), Ghidra-synthesized stack-variable
    suffixes (`auStack_38`, `pcStack_20`, etc.), and decompiler warning
    comments referencing absolute addresses. Two decompiled bodies that
    differ only in these artifacts are semantically identical — the byte
    change is a binary rebase, not a code change.
    """
    code = _GHIDRA_COMMENT_RE.sub("// GHIDRA_NOTE", code)
    code = _FUNC_REF_RE.sub("FUNC_REF", code)
    code = _LABEL_REF_RE.sub("LABEL_REF", code)
    code = _ADDR_RE.sub("ADDR", code)
    code = _STACK_VAR_RE.sub(r"\1OFF", code)
    return code


def is_rebase_noise(a: str, b: str) -> bool:
    """True if two decompiled bodies differ only in address artifacts."""
    if a == b:
        return False
    return normalize_decompiled(a) == normalize_decompiled(b)


def _rewrite_in_order(code: str, pattern: re.Pattern, alias_prefix: str) -> str:
    """Replace each unique match of `pattern` in `code` with `alias_prefix_N`,
    where N is the 1-indexed order of first occurrence. Stable per body.
    """
    mapping: dict[str, str] = {}

    def repl(m: re.Match) -> str:
        token = m.group(0)
        if token not in mapping:
            mapping[token] = f"{alias_prefix}_{len(mapping) + 1}"
        return mapping[token]

    return pattern.sub(repl, code)


def canonicalize_for_llm(code_a: str, code_b: str) -> tuple[str, str]:
    """Rename volatile Ghidra artifacts to stable aliases before showing the
    pair to an LLM.

    `func_0xNNNN`, `code_r0xNNNN`, and bare `0xNNNN` literals get rewritten
    to `HELPER_N`, `LABEL_N`, `ADDR_N` based on their order of first
    appearance *within each body independently*. When the two functions are
    semantically identical, both bodies reference helpers in the same order
    at the same call sites, so the aliases line up and the rebase noise
    disappears from the diff the LLM sees. When the order diverges, that
    divergence is the real semantic change — exactly what we want surfaced.

    Stack-variable suffixes (`auStack_38`) are also normalized; they shift
    on every recompile because of frame-layout drift but rarely carry
    meaning at the C level.

    Decompiler comment lines (`WARNING: ... 0xNNNN`) are stripped because
    they are pure noise.
    """
    def one(code: str) -> str:
        code = _GHIDRA_COMMENT_RE.sub("", code)
        code = _rewrite_in_order(code, _FUNC_REF_RE, "HELPER")
        code = _rewrite_in_order(code, _LABEL_REF_RE, "LABEL")
        code = _rewrite_in_order(code, _ADDR_RE, "ADDR")
        # Stack-var suffixes get a single neutral marker — preserving
        # ordering would over-segment unrelated locals.
        code = _STACK_VAR_RE.sub(r"\1OFF", code)
        return code

    return one(code_a), one(code_b)


class Function(BaseModel):
    """Represents a decompiled function."""
    name: str
    signature: str
    decompiled: str
    address: str


class FunctionDiff(BaseModel):
    """Represents the difference between two matched functions."""
    name: str
    func_a: Optional[Function] = None
    func_b: Optional[Function] = None
    status: str  # "added", "removed", "modified", "unchanged", "renamed"
    similarity: float = 1.0


class DiffEngine:
    """Matches functions between two binaries and identifies changes."""

    def __init__(self, threshold: float = 0.85):
        """Initialize DiffEngine.

        Args:
            threshold: Similarity threshold for fuzzy matching (0.0 to 1.0)
        """
        self.threshold = threshold

    def compute_diff(
        self, 
        funcs_a: List[Dict], 
        funcs_b: List[Dict],
        external_matches: Optional[Dict[str, str]] = None
    ) -> List[FunctionDiff]:
        """Match functions and categorize changes.

        Args:
            funcs_a: Functions from binary A
            funcs_b: Functions from binary B
            external_matches: Dict mapping name_a -> name_b from external tool

        Returns:
            List of FunctionDiff objects
        """
        map_a = {f["name"]: Function(**f) for f in funcs_a}
        map_b = {f["name"]: Function(**f) for f in funcs_b}
        
        diffs = []
        matched_names_a = set()
        matched_names_b = set()

        # 0. External matches (BinDiff/Diaphora import)
        if external_matches:
            for name_a, name_b in external_matches.items():
                if name_a in map_a and name_b in map_b:
                    fa, fb = map_a[name_a], map_b[name_b]
                    if fa.decompiled == fb.decompiled:
                        status = "unchanged"
                    elif is_rebase_noise(fa.decompiled, fb.decompiled):
                        status = "noise"
                    else:
                        status = "modified"
                    diffs.append(FunctionDiff(
                        name=f"{name_a} <-> {name_b}" if name_a != name_b else name_a,
                        func_a=fa, func_b=fb, status=status
                    ))
                    matched_names_a.add(name_a)
                    matched_names_b.add(name_b)

        # 1. Exact matches by name
        common_names = (set(map_a.keys()) & set(map_b.keys())) - matched_names_a
        for name in common_names:
            if name in matched_names_b: 
                continue
            
            fa = map_a[name]
            fb = map_b[name]
            
            if fa.decompiled == fb.decompiled:
                status = "unchanged"
            elif is_rebase_noise(fa.decompiled, fb.decompiled):
                status = "noise"
            else:
                status = "modified"

            diffs.append(FunctionDiff(name=name, func_a=fa, func_b=fb, status=status))
            matched_names_a.add(name)
            matched_names_b.add(name)

        # 2. Fuzzy matching for remaining functions (Renames)
        unmatched_a = [map_a[name] for name in map_a if name not in matched_names_a]
        unmatched_b = [map_b[name] for name in map_b if name not in matched_names_b]
        
        for fa in unmatched_a:
            best_match = None
            best_score = 0.0
            
            for fb in unmatched_b:
                if fb.name in matched_names_b:
                    continue
                
                # Compare decompiled code similarity
                score = difflib.SequenceMatcher(None, fa.decompiled, fb.decompiled).quick_ratio()
                
                if score > best_score and score >= self.threshold:
                    best_score = score
                    best_match = fb
            
            if best_match:
                diffs.append(FunctionDiff(
                    name=f"{fa.name} -> {best_match.name}",
                    func_a=fa,
                    func_b=best_match,
                    status="renamed",
                    similarity=best_score
                ))
                matched_names_a.add(fa.name)
                matched_names_b.add(best_match.name)

        # 3. Add remaining added/removed
        for name, fa in map_a.items():
            if name not in matched_names_a:
                diffs.append(FunctionDiff(name=name, func_a=fa, status="removed"))
        
        for name, fb in map_b.items():
            if name not in matched_names_b:
                diffs.append(FunctionDiff(name=name, func_b=fb, status="added"))
                
        return diffs
