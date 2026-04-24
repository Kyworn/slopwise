"""Tests for the diffing engine."""

from slopwise.diff import DiffEngine


def test_exact_match():
    engine = DiffEngine()
    funcs_a = [{"name": "main", "signature": "int main()", "decompiled": "return 0;", "address": "0x100"}]
    funcs_b = [{"name": "main", "signature": "int main()", "decompiled": "return 0;", "address": "0x100"}]
    
    diffs = engine.compute_diff(funcs_a, funcs_b)
    assert len(diffs) == 1
    assert diffs[0].status == "unchanged"


def test_fuzzy_match_rename():
    engine = DiffEngine(threshold=0.5)
    # Different names but similar code
    funcs_a = [{"name": "old_func", "signature": "void f()", "decompiled": "int x = 1; return x;", "address": "0x100"}]
    funcs_b = [{"name": "new_func", "signature": "void f()", "decompiled": "int x = 1; return x;", "address": "0x200"}]
    
    diffs = engine.compute_diff(funcs_a, funcs_b)
    assert len(diffs) == 1
    assert diffs[0].status == "renamed"
    assert "old_func -> new_func" in diffs[0].name


def test_modified():
    engine = DiffEngine()
    funcs_a = [{"name": "main", "signature": "int main()", "decompiled": "return 0;", "address": "0x100"}]
    funcs_b = [{"name": "main", "signature": "int main()", "decompiled": "return 1;", "address": "0x100"}]
    
    diffs = engine.compute_diff(funcs_a, funcs_b)
    assert diffs[0].status == "modified"
