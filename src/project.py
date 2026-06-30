# """
# Projection layer.

# Transforms a canonical CandidateProfile into the output schema
# specified by a runtime JSON configuration.
# """

# import json
# from pathlib import Path

# from src.schema import CandidateProfile


# CONFIG_PATH = Path("config/projection.json")


# def load_projection_config() -> dict:
#     """Loads the runtime projection configuration."""
#     with open(CONFIG_PATH, "r", encoding="utf-8") as f:
#         return json.load(f)


# def _replace_missing(value, replacement):
#     """
#     Recursively replaces None values with the configured missing value.
#     """
#     if value is None:
#         return replacement

#     if isinstance(value, dict):
#         return {
#             k: _replace_missing(v, replacement)
#             for k, v in value.items()
#         }

#     if isinstance(value, list):
#         return [
#             _replace_missing(v, replacement)
#             for v in value
#         ]

#     return value


# def project_profile(profile: CandidateProfile,
#                     config: dict | None = None) -> dict:
#     """
#     Projects a canonical profile according to the runtime config.
#     """

#     if config is None:
#         config = load_projection_config()

#     profile_dict = profile.model_dump()

#     projected = {}

#     wanted_fields = config.get("fields", [])

#     rename = config.get("rename", {})

#     include_confidence = config.get(
#         "include_confidence",
#         True
#     )

#     include_provenance = config.get(
#         "include_provenance",
#         True
#     )

#     missing_value = config.get(
#         "missing_value",
#         None
#     )

#     for field in wanted_fields:

#         if field == "overall_confidence" and not include_confidence:
#             continue

#         if field == "provenance" and not include_provenance:
#             continue

#         if field not in profile_dict:
#             continue

#         output_name = rename.get(field, field)

#         projected[output_name] = _replace_missing(
#             profile_dict[field],
#             missing_value,
#         )

#     return projected


# if __name__ == "__main__":

#     from src.merge import merge_all
#     from src.ingest_csv import ingest_csv
#     from src.ingest_resume import ingest_resume
#     from pathlib import Path
#     import json

#     records = []

#     records.extend(ingest_csv("sample_inputs/recruiter.csv"))

#     for pdf in Path("sample_inputs").glob("resume_*.pdf"):
#         records.append(ingest_resume(str(pdf)))

#     profiles = merge_all(records)

#     config = load_projection_config()

#     print("\nProjected Profiles\n")

#     for profile in profiles:
#         print(
#             json.dumps(
#                 project_profile(profile, config),
#                 indent=2,
#             )
#         )
#         print("-" * 60)
"""
Projection layer — reshapes a canonical CandidateProfile into a
custom output shape defined by a runtime config (Section 4 of design doc).

The canonical record is always built in full first (by merge.py).
This layer is purely a presentation/reshaping concern — it never
touches the merge engine or raw source data.

Config shape:
{
  "fields": [
    {"path": "full_name", "type": "string", "required": true},
    {"path": "primary_email", "from": "emails[0]", "type": "string"},
    {"path": "phone", "from": "phones[0]", "type": "string", "normalize": "E164"},
    {"path": "skills", "from": "skills[].name", "type": "string[]"}
  ],
  "include_confidence": true,
  "include_provenance": false,
  "on_missing": "null"   // "null" | "omit" | "error"
}
"""

import re
from src.schema import CandidateProfile


# Default config — outputs the full canonical schema, no renaming,
# confidence and provenance both included.
DEFAULT_CONFIG = {
    "fields": [
        {"path": "candidate_id",       "type": "string",   "required": True},
        {"path": "full_name",          "type": "string"},
        {"path": "emails",             "type": "string[]"},
        {"path": "phones",             "type": "string[]"},
        {"path": "location",           "type": "object"},
        {"path": "links",              "type": "object"},
        {"path": "headline",           "type": "string"},
        {"path": "years_experience",   "type": "number"},
        {"path": "skills",             "type": "object[]"},
        {"path": "experience",         "type": "object[]"},
        {"path": "education",          "type": "object[]"},
    ],
    "include_confidence": True,
    "include_provenance": True,
    "on_missing": "null",
}


def load_projection_config(config: dict | None = None) -> dict:
    """
    Returns the config to use for projection.
    If no config is passed, returns the default (full canonical schema).
    """
    if config is None:
        return DEFAULT_CONFIG
    return config


def _resolve_path(data: dict, path: str):
    """
    Resolves a dot/bracket path against a dict.
    Supports:
      - Simple fields:     "full_name"
      - Array index:       "emails[0]"
      - Array pluck:       "skills[].name"  (returns list of that field)
    Returns the resolved value, or None if path doesn't exist.
    """
    # emails[0] style
    index_match = re.match(r"^(\w+)\[(\d+)\]$", path)
    if index_match:
        field, idx = index_match.group(1), int(index_match.group(2))
        arr = data.get(field, [])
        return arr[idx] if isinstance(arr, list) and len(arr) > idx else None

    # skills[].name style — pluck a field from every item in the array
    pluck_match = re.match(r"^(\w+)\[\]\.(\w+)$", path)
    if pluck_match:
        field, subfield = pluck_match.group(1), pluck_match.group(2)
        arr = data.get(field, [])
        if isinstance(arr, list):
            return [item.get(subfield) for item in arr if isinstance(item, dict) and subfield in item]
        return None

    # Simple field or nested dot path
    parts = path.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def project_profile(profile: CandidateProfile, config: dict) -> dict:
    """
    Projects a CandidateProfile into a custom output shape defined by config.
    Returns a plain dict (ready for JSON serialisation).
    """
    # Convert profile to a plain dict first
    data = profile.model_dump()

    on_missing = config.get("on_missing", "null")
    include_confidence = config.get("include_confidence", True)
    include_provenance = config.get("include_provenance", True)
    fields = config.get("fields", DEFAULT_CONFIG["fields"])

    result = {}

    for field_spec in fields:
        output_path = field_spec["path"]
        source_path = field_spec.get("from", output_path)
        required = field_spec.get("required", False)

        value = _resolve_path(data, source_path)

        # Handle missing values
        if value is None:
            if required and on_missing == "error":
                raise ValueError(f"Required field '{output_path}' is missing")
            elif on_missing == "omit":
                continue
            else:
                result[output_path] = None
        else:
            result[output_path] = value

    # Append confidence / provenance based on toggles
    if include_confidence:
        result["overall_confidence"] = data.get("overall_confidence")

    if include_provenance:
        result["provenance"] = data.get("provenance", [])

    return result


if __name__ == "__main__":
    # Quick test using the default config
    from src.ingest_csv import ingest_csv
    from src.ingest_resume import ingest_resume
    from src.merge import merge_all

    csv_records = ingest_csv("sample_inputs/recruiter.csv")
    resume_record = ingest_resume("sample_inputs/resume_bushra.pdf")
    profiles = merge_all(csv_records + [resume_record])

    config = load_projection_config()

    print("=== DEFAULT CONFIG OUTPUT ===")
    import json
    for p in profiles[:1]:
        projected = project_profile(p, config)
        print(json.dumps(projected, indent=2))