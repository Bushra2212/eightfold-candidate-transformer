"""
Tests for candidate matching and merging.

Run:
    pytest tests/test_merge.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.schema import RawRecord
from src.merge import _is_match


def test_email_match():
    """
    Same email should always match.
    """

    r1 = RawRecord(
        source_type="csv",
        source_id="1",
        full_name="Bushra Khan",
        emails=["bushra@example.com"],
        phones=[],
        company="TechCorp",
        title="Engineer",
    )

    r2 = RawRecord(
        source_type="resume",
        source_id="2",
        full_name="Bushra Khan",
        emails=["bushra@example.com"],
        phones=[],
        company="TechCorp",
        title="Software Engineer",
    )

    matched, reason, score = _is_match(r1, r2)

    assert matched
    assert reason == "email_match"
    assert score >= 0.90


def test_phone_match():
    """
    Same phone should match even if emails differ.
    """

    r1 = RawRecord(
        source_type="csv",
        source_id="1",
        emails=["old@example.com"],
        phones=["+919876543210"],
        company="TechCorp",
    )

    r2 = RawRecord(
        source_type="resume",
        source_id="2",
        emails=["new@example.com"],
        phones=["+919876543210"],
        company="TechCorp",
    )

    matched, reason, score = _is_match(r1, r2)

    assert matched
    assert reason == "phone_match"
    assert score >= 0.85


def test_contradiction_veto():
    """
    Different email AND different phone should never merge,
    even if name/company are identical.
    """

    r1 = RawRecord(
        source_type="csv",
        source_id="1",
        full_name="Karan Shah",
        emails=["karan1@example.com"],
        phones=["+918877665544"],
        company="NextGen Labs",
        title="DevOps Engineer",
    )

    r2 = RawRecord(
        source_type="csv",
        source_id="2",
        full_name="Karan Shah",
        emails=["karan2@example.com"],
        phones=["+918800000000"],
        company="NextGen Labs",
        title="DevOps Engineer",
    )

    matched, reason, score = _is_match(r1, r2)

    assert matched is False
    assert score == 0.0


def test_name_company_low_confidence():
    """
    Same name + company is considered a weak match,
    but should receive a low confidence score.
    The actual merge decision is taken later by
    match_records() using MATCH_THRESHOLD.
    """

    r1 = RawRecord(
        source_type="csv",
        source_id="1",
        full_name="Bushra Khan",
        emails=["bushra@example.com"],
        phones=[],
        company="TechCorp",
    )

    r2 = RawRecord(
        source_type="csv",
        source_id="2",
        full_name="Bushra Khan",
        emails=[],
        phones=[],
        company="TechCorp",
    )

    matched, reason, score = _is_match(r1, r2)

    assert matched is True
    assert reason == "name_and_company_match"
    assert score == 0.40