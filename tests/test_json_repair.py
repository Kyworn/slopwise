"""Tests for lenient JSON parsing of LLM outputs."""

import json

import pytest

from slopwise.json_repair import loads_lenient


def test_clean_json():
    assert loads_lenient('{"a": 1}') == {"a": 1}


def test_markdown_fence():
    text = 'sure!\n```json\n{"a": 1}\n```\n'
    assert loads_lenient(text) == {"a": 1}


def test_bare_fence():
    text = '```\n{"a": 1}\n```'
    assert loads_lenient(text) == {"a": 1}


def test_leading_prose():
    text = 'Here is the analysis:\n{"a": 1, "b": "x"}\nthanks.'
    assert loads_lenient(text) == {"a": 1, "b": "x"}


def test_trailing_comma():
    text = '{"a": 1, "b": [1, 2,],}'
    assert loads_lenient(text) == {"a": 1, "b": [1, 2]}


def test_braces_inside_string_dont_confuse_extractor():
    text = '{"summary": "if (x > 0) { return; }"}'
    assert loads_lenient(text) == {"summary": "if (x > 0) { return; }"}


def test_no_json_raises():
    with pytest.raises(json.JSONDecodeError):
        loads_lenient("totally not json at all")
