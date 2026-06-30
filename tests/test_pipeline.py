# """
# End-to-end pipeline tests.

# Run:
#     pytest tests/test_pipeline.py
# """
# import sys
# from pathlib import Path

# # Add project root to Python path
# sys.path.append(str(Path(__file__).resolve().parents[1]))

# from src.pipeline import run_pipeline


# def test_pipeline_runs_successfully():
#     """
#     Verifies that the complete pipeline executes without errors
#     and returns at least one projected candidate profile.
#     """

#     profiles = run_pipeline(
#         csv_path="sample_inputs/recruiter.csv",
#         resume_folder="sample_inputs",
#     )

#     assert isinstance(profiles, list)
#     assert len(profiles) > 0


# def test_pipeline_candidate_fields():
#     """
#     Every projected profile should contain the expected
#     output fields defined by projection.json.
#     """

#     profiles = run_pipeline(
#         csv_path="sample_inputs/recruiter.csv",
#         resume_folder="sample_inputs",
#     )

#     required_fields = {
#         "candidate_id",
#         "candidate_name",
#         "emails",
#         "phones",
#         "skills",
#         "overall_confidence",
#         "provenance",
#     }

#     for profile in profiles:
#         assert required_fields.issubset(profile.keys())


# def test_pipeline_confidence_range():
#     """
#     Confidence scores should always lie between 0 and 1.
#     """

#     profiles = run_pipeline(
#         csv_path="sample_inputs/recruiter.csv",
#         resume_folder="sample_inputs",
#     )

#     for profile in profiles:
#         confidence = profile["overall_confidence"]
#         assert 0.0 <= confidence <= 1.0


# def test_pipeline_unique_candidate_ids():
#     """
#     Every projected profile should have a unique candidate_id.
#     """

#     profiles = run_pipeline(
#         csv_path="sample_inputs/recruiter.csv",
#         resume_folder="sample_inputs",
#     )

#     ids = [p["candidate_id"] for p in profiles]

#     assert len(ids) == len(set(ids))
"""
Basic tests for the Eightfold Candidate Transformation Pipeline.
Covers the core engine + one edge case per major component.

Run with: python -m pytest tests/ -v
"""

import pytest
from src.ingest_csv import ingest_csv
from src.ingest_resume import ingest_resume
from src.normalize import normalize_phone, normalize_date, normalize_skills
from src.merge import merge_all, _is_match
from src.schema import RawRecord
from src.project import load_projection_config, project_profile
from src.validate import validate_profile
from src.pipeline import run_pipeline


# ----------------------------------------------------------------
# normalize.py tests
# ----------------------------------------------------------------

def test_normalize_phone_e164():
    assert normalize_phone("9876543210") == "+919876543210"

def test_normalize_phone_with_country_code():
    assert normalize_phone("+91 9876543210") == "+919876543210"

def test_normalize_phone_invalid_returns_none():
    assert normalize_phone("not-a-phone") is None

def test_normalize_date_text():
    assert normalize_date("Jan 2022") == "2022-01"

def test_normalize_date_iso():
    assert normalize_date("2022-01") == "2022-01"

def test_normalize_date_present_returns_none():
    assert normalize_date("Present") is None

def test_normalize_skills_canonical():
    assert normalize_skills(["JS", "python", "AWS"]) == ["JavaScript", "Python", "AWS"]

def test_normalize_skills_dedupes():
    assert normalize_skills(["Python", "python", "PYTHON"]) == ["Python"]


# ----------------------------------------------------------------
# merge.py tests — matching policy
# ----------------------------------------------------------------

def _make_record(source_type="csv", source_id="test", **kwargs) -> RawRecord:
    return RawRecord(source_type=source_type, source_id=source_id, **kwargs)


def test_match_email():
    a = _make_record(emails=["same@example.com"], phones=[])
    b = _make_record(emails=["same@example.com"], phones=[])
    matched, reason, *_ = _is_match(a, b)
    assert matched is True
    assert reason == "email_match"

def test_match_phone():
    a = _make_record(emails=[], phones=["9876543210"])
    b = _make_record(emails=[], phones=["9876543210"])
    matched, reason, *_ = _is_match(a, b)
    assert matched is True
    assert reason == "phone_match"

def test_no_match_different_email_and_phone():
    a = _make_record(emails=["a@x.com"], phones=["1111111111"])
    b = _make_record(emails=["b@x.com"], phones=["2222222222"])
    matched, reason, *_ = _is_match(a, b)
    assert matched is False

def test_no_match_missing_email_and_phone():
    """
    Edge case: both records have no email and no phone.
    Should NOT merge, even if name and company match.
    """
    a = _make_record(emails=[], phones=[], full_name="John Doe", company="Acme")
    b = _make_record(emails=[], phones=[], full_name="John Doe", company="Acme")
    matched, reason, *_ = _is_match(a, b)
    assert matched is False

def test_match_email_wins_over_different_phone():
    """
    If email matches, merge should proceed even if phones differ.
    A person can have multiple phone numbers.
    """
    a = _make_record(emails=["same@x.com"], phones=["1111111111"])
    b = _make_record(emails=["same@x.com"], phones=["2222222222"])
    matched, reason, *_ = _is_match(a, b)
    assert matched is True
    assert reason == "email_match"

# ----------------------------------------------------------------
# pipeline integration test
# ----------------------------------------------------------------

def test_pipeline_runs_end_to_end():
    results = run_pipeline(
        csv_path="sample_inputs/recruiter.csv",
        resume_folder="sample_inputs",
        output_config=None,
    )
    assert isinstance(results, list)
    assert len(results) > 0
    for profile in results:
        assert "candidate_id" in profile
        assert "full_name" in profile

def test_pipeline_custom_config():
    """
    The configurable output layer must rename fields correctly
    and strip provenance when include_provenance is false.
    """
    import json, os
    with open("config/example_config.json") as f:
        config = json.load(f)

    results = run_pipeline(
        csv_path="sample_inputs/recruiter.csv",
        resume_folder="sample_inputs",
        output_config=config,
    )
    assert len(results) > 0
    first = results[0]
    # Renamed fields must exist
    assert "primary_email" in first
    assert "phone" in first
    # Original field names must NOT exist (they were renamed)
    assert "emails" not in first
    assert "phones" not in first
    # Provenance must be stripped
    assert "provenance" not in first