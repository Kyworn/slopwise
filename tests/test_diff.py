"""Tests for the diffing engine."""

from slopwise.diff import DiffEngine, is_rebase_noise, normalize_decompiled


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


def test_rebase_noise_detected():
    a = "func_0x00102230(x); goto code_r0x00104dee;"
    b = "func_0x00102220(x); goto code_r0x00104dd7;"
    assert is_rebase_noise(a, b)
    assert normalize_decompiled(a) == normalize_decompiled(b)


def test_real_change_not_noise():
    a = "func_0x00102230(x); return 0;"
    b = "func_0x00102220(x); return 1;"
    assert not is_rebase_noise(a, b)


def test_stack_var_offset_is_noise():
    a = "int x = auStack_38[0]; pcStack_20 = lStack_18;"
    b = "int x = auStack_2c[0]; pcStack_14 = lStack_0c;"
    assert is_rebase_noise(a, b)


def test_ghidra_warning_comment_is_noise():
    a = "// WARNING: Removing unreachable block at 0x001022b4\nreturn 0;"
    b = "// WARNING: Removing unreachable block at 0x001022a4\nreturn 0;"
    assert is_rebase_noise(a, b)


def test_struct_offsets_preserved():
    """Small hex literals like 0x10, 0x40 are real struct offsets, not noise."""
    a = "x = *(long *)(p + 0x10); y = *(long *)(p + 0x40);"
    b = "x = *(long *)(p + 0x18); y = *(long *)(p + 0x40);"
    assert not is_rebase_noise(a, b)


def test_noise_status_in_diff():
    engine = DiffEngine()
    funcs_a = [{
        "name": "f",
        "signature": "void f()",
        "decompiled": "func_0x00102230(x); goto code_r0x00104dee;",
        "address": "0x100",
    }]
    funcs_b = [{
        "name": "f",
        "signature": "void f()",
        "decompiled": "func_0x00102220(x); goto code_r0x00104dd7;",
        "address": "0x100",
    }]
    diffs = engine.compute_diff(funcs_a, funcs_b)
    assert diffs[0].status == "noise"
