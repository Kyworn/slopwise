"""Schema validation for agent outputs."""

import pytest
from pydantic import ValidationError

from slopwise.agents.schemas import (
    CATEGORIES,
    RISKS,
    AnalysisResult,
    ClusterResult,
    CriticResult,
)


def test_categories_and_risks_are_what_we_advertise():
    assert set(CATEGORIES) == {"bugfix", "feature", "refactor", "security", "other"}
    assert set(RISKS) == {"low", "medium", "high"}


def test_analysis_round_trip():
    payload = {
        "category": "bugfix",
        "risk": "low",
        "summary": "fixed a thing",
        "details": "in detail",
    }
    result = AnalysisResult.model_validate(payload).model_dump()
    assert result["category"] == "bugfix"
    assert result["risk"] == "low"
    assert result["summary"] == "fixed a thing"
    assert result["details"] == "in detail"


def test_analysis_rejects_invented_category():
    with pytest.raises(ValidationError):
        AnalysisResult.model_validate({
            "category": "Bugfix/logic",
            "risk": "low",
            "summary": "x",
        })


def test_analysis_rejects_capitalized_risk():
    with pytest.raises(ValidationError):
        AnalysisResult.model_validate({
            "category": "bugfix",
            "risk": "MEDIUM",
            "summary": "x",
        })


def test_analysis_drops_extra_fields_quietly():
    """`extra=ignore` so future LLM outputs adding fields don't break us."""
    result = AnalysisResult.model_validate({
        "category": "refactor",
        "risk": "low",
        "summary": "x",
        "imaginary_new_field": "whatever",
    })
    assert "imaginary_new_field" not in result.model_dump()


def test_critic_approved_keeps_no_adjustment():
    cr = CriticResult.model_validate({"approved": True, "flags": []})
    assert cr.approved is True
    assert cr.adjusted_analysis is None


def test_critic_with_adjusted_analysis():
    cr = CriticResult.model_validate({
        "approved": False,
        "flags": ["missed bounds check on line 4"],
        "adjusted_analysis": {
            "category": "security",
            "risk": "high",
            "summary": "OOB write",
        },
    })
    assert cr.adjusted_analysis is not None
    assert cr.adjusted_analysis.risk == "high"


def test_cluster_result():
    cr = ClusterResult.model_validate({
        "themes": {"Memory": ["a", "b"], "I/O": ["c"]},
    })
    assert cr.themes == {"Memory": ["a", "b"], "I/O": ["c"]}
