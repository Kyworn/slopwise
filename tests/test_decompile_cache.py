"""Tests for the decompilation content-hash cache."""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from slopwise.config import GhidraConfig
from slopwise.decompile import Decompiler


@pytest.fixture
def fake_ghidra(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a fake Ghidra layout that satisfies the FileNotFoundError check
    in `Decompiler.__init__`, and isolate the cache to a temp dir."""
    ghidra_home = tmp_path / "ghidra"
    (ghidra_home / "support").mkdir(parents=True)
    (ghidra_home / "support" / "analyzeHeadless").write_text("#!/bin/sh\nexit 0\n")
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    return ghidra_home


def _decompiler(ghidra_home: Path, use_cache: bool = True) -> Decompiler:
    return Decompiler(GhidraConfig(ghidra_home=ghidra_home), use_cache=use_cache)


def test_cache_key_changes_with_binary_bytes(tmp_path: Path, fake_ghidra: Path):
    d = _decompiler(fake_ghidra)
    bin_a = tmp_path / "a.bin"
    bin_b = tmp_path / "b.bin"
    bin_a.write_bytes(b"\x01\x02\x03")
    bin_b.write_bytes(b"\x01\x02\x04")
    assert d.cache_key(bin_a) != d.cache_key(bin_b)


def test_cache_hit_skips_ghidra(tmp_path: Path, fake_ghidra: Path):
    d = _decompiler(fake_ghidra)
    binary = tmp_path / "x.bin"
    binary.write_bytes(b"hello")

    expected = [{"name": "main", "decompiled": "return 0;", "signature": "", "address": "0x0"}]

    # First run: actually invoke `_run_ghidra` and let it populate the cache.
    with patch.object(Decompiler, "_run_ghidra", return_value=expected) as mock_run:
        out = d.decompile(binary)
    assert out == expected
    assert mock_run.call_count == 1

    # Second run: cache hit, must NOT call into Ghidra.
    with patch.object(Decompiler, "_run_ghidra", return_value=[]) as mock_run:
        out = d.decompile(binary)
    assert out == expected
    assert mock_run.call_count == 0


def test_no_cache_flag_forces_rerun(tmp_path: Path, fake_ghidra: Path):
    binary = tmp_path / "x.bin"
    binary.write_bytes(b"hello")
    expected = [{"name": "main", "decompiled": "x", "signature": "", "address": "0x0"}]

    cached = _decompiler(fake_ghidra, use_cache=True)
    with patch.object(Decompiler, "_run_ghidra", return_value=expected):
        cached.decompile(binary)

    fresh = _decompiler(fake_ghidra, use_cache=False)
    with patch.object(Decompiler, "_run_ghidra", return_value=expected) as mock_run:
        out = fresh.decompile(binary)
    assert out == expected
    assert mock_run.call_count == 1


def test_corrupt_cache_is_ignored(tmp_path: Path, fake_ghidra: Path):
    d = _decompiler(fake_ghidra)
    binary = tmp_path / "x.bin"
    binary.write_bytes(b"hello")

    # Hand-write a broken cache entry under the expected key.
    key = d.cache_key(binary)
    cache_dir = Path(os.environ["XDG_CACHE_HOME"]) / "slopwise" / "decomp"
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / f"{key}.json").write_text("{not json")

    expected = [{"name": "main", "decompiled": "x", "signature": "", "address": "0x0"}]
    with patch.object(Decompiler, "_run_ghidra", return_value=expected) as mock_run:
        out = d.decompile(binary)
    assert out == expected
    assert mock_run.call_count == 1
    # And it should overwrite the bad cache with valid JSON now.
    assert json.loads((cache_dir / f"{key}.json").read_text()) == expected
