"""Function matching and diffing logic with fuzzy matching support."""

import difflib
from typing import Dict, List, Optional, Set, Tuple

from pydantic import BaseModel


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
                    status = "unchanged" if fa.decompiled == fb.decompiled else "modified"
                    diffs.append(FunctionDiff(
                        name=f"{name_a} <-> {name_b}" if name_a != name_b else name_a,
                        func_a=fa, func_b=fb, status=status
                    ))
                    matched_names_a.add(name_a)
                    matched_names_b.add(name_b)

        # 1. Exact matches by name
        common_names = (set(map_a.keys()) & set(map_b.keys())) - matched_names_a
        for name in common_names:
            if name in matched_names_b: continue
            fa = map_a[name]
            fb = map_b[name]
            
            if fa.decompiled == fb.decompiled:
                status = "unchanged"
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
