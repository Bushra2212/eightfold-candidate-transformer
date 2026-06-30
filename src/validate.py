# """
# Validation layer.

# Checks that the projected output matches the runtime projection config.
# Runs AFTER project.py.
# """

# from typing import Any


# def validate_profile(profile: dict, config: dict) -> tuple[bool, list[str]]:
#     """
#     Validates one projected profile.

#     Returns:
#         (True, []) if valid
#         (False, [errors]) otherwise.
#     """

#     errors = []

#     expected_fields = set(config.get("fields", []))

#     rename = config.get("rename", {})

#     expected_output_fields = {
#         rename.get(field, field)
#         for field in expected_fields
#     }

#     # Remove optional fields if config disables them
#     if not config.get("include_confidence", True):
#         expected_output_fields.discard(
#             rename.get("overall_confidence", "overall_confidence")
#         )

#     if not config.get("include_provenance", True):
#         expected_output_fields.discard(
#             rename.get("provenance", "provenance")
#         )

#     actual_fields = set(profile.keys())

#     # -------------------------
#     # Missing fields
#     # -------------------------
#     missing = expected_output_fields - actual_fields

#     if missing:
#         errors.append(
#             f"Missing fields: {sorted(missing)}"
#         )

#     # -------------------------
#     # Unexpected fields
#     # -------------------------
#     extra = actual_fields - expected_output_fields

#     if extra:
#         errors.append(
#             f"Unexpected fields: {sorted(extra)}"
#         )

#     # -------------------------
#     # Confidence range
#     # -------------------------
#     confidence_key = rename.get(
#         "overall_confidence",
#         "overall_confidence"
#     )

#     if confidence_key in profile:

#         confidence = profile[confidence_key]

#         if not isinstance(confidence, (int, float)):
#             errors.append(
#                 "overall_confidence must be numeric"
#             )

#         elif not (0 <= confidence <= 1):
#             errors.append(
#                 "overall_confidence must be between 0 and 1"
#             )

#     return len(errors) == 0, errors


# if __name__ == "__main__":

#     import json

#     from src.project import (
#         load_projection_config,
#         project_profile,
#     )

#     from src.merge import merge_all
#     from src.ingest_csv import ingest_csv
#     from src.ingest_resume import ingest_resume
#     from pathlib import Path

#     records = []

#     records.extend(
#         ingest_csv("sample_inputs/recruiter.csv")
#     )

#     for pdf in Path("sample_inputs").glob("resume_*.pdf"):
#         records.append(
#             ingest_resume(str(pdf))
#         )

#     profiles = merge_all(records)

#     config = load_projection_config()

#     print("\nValidation Results\n")

#     for profile in profiles:

#         projected = project_profile(profile, config)

#         valid, errors = validate_profile(
#             projected,
#             config,
#         )

#         print(projected["candidate_id"])

#         if valid:
#             print("PASS")
#         else:
#             print("FAIL")
#             for err in errors:
#                 print(" -", err)

#         print("-" * 60)
"""
Validates a projected output dict against the requested config schema.
Checks types and required fields — catches typos in 'from' paths or
schema mismatches before they reach the caller.
"""


TYPE_VALIDATORS = {
    "string": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, (int, float)),
    "string[]": lambda v: isinstance(v, list) and all(isinstance(i, str) for i in v),
    "object": lambda v: isinstance(v, dict),
    "object[]": lambda v: isinstance(v, list) and all(isinstance(i, dict) for i in v),
}


def validate_profile(profile: dict, config: dict) -> tuple[bool, list[str]]:
    """
    Validates a projected profile dict against the config's field specs.
    Returns (is_valid: bool, errors: list[str]).
    Degrades gracefully — never raises, always returns errors as a list.
    """
    errors = []
    fields = config.get("fields", [])

    for field_spec in fields:
        path = field_spec["path"]
        expected_type = field_spec.get("type")
        required = field_spec.get("required", False)

        value = profile.get(path)

        # Required field missing
        if required and value is None:
            errors.append(f"Required field '{path}' is null or missing")
            continue

        # Skip type check if value is null and not required
        if value is None:
            continue

        # Type check
        if expected_type and expected_type in TYPE_VALIDATORS:
            if not TYPE_VALIDATORS[expected_type](value):
                errors.append(
                    f"Field '{path}' expected type '{expected_type}' "
                    f"but got {type(value).__name__}: {repr(value)[:50]}"
                )

    is_valid = len(errors) == 0
    return is_valid, errors


if __name__ == "__main__":
    # Quick sanity test
    test_profile = {
        "candidate_id": "cand_0001",
        "full_name": "Bushra Khan",
        "emails": ["bushra.khan@example.com"],
        "phones": ["+919876543210"],
        "overall_confidence": 0.79,
    }

    test_config = {
        "fields": [
            {"path": "candidate_id", "type": "string", "required": True},
            {"path": "full_name",    "type": "string", "required": True},
            {"path": "emails",       "type": "string[]"},
            {"path": "phones",       "type": "string[]"},
        ],
        "include_confidence": True,
        "include_provenance": False,
        "on_missing": "null",
    }

    valid, errors = validate_profile(test_profile, test_config)
    print(f"Valid: {valid}")
    if errors:
        for e in errors:
            print(f"  - {e}")
    else:
        print("All fields passed validation.")