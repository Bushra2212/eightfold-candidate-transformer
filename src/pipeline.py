# """
# End-to-end candidate transformation pipeline.

# Flow:
# CSV + Resume(s)
#         ↓
# Raw Records
#         ↓
# Merge
#         ↓
# Canonical CandidateProfiles
#         ↓
# Projection
#         ↓
# Validation
#         ↓
# Final Output
# """

# from pathlib import Path

# from src.ingest_csv import ingest_csv
# from src.ingest_resume import ingest_resume
# from src.merge import merge_all
# from src.project import load_projection_config, project_profile
# from src.validate import validate_profile


# def run_pipeline(csv_path: str, resume_folder: str):
#     """
#     Runs the complete pipeline.

#     Returns:
#         List of validated projected profiles.
#     """

#     print("\n" + "=" * 70)
#     print("        EIGHTFOLD CANDIDATE TRANSFORMATION PIPELINE")
#     print("=" * 70)

#     print(
#         """
# Workflow

# Structured CSV
#       │
#       ▼
# Unstructured Resume PDFs
#       │
#       ▼
# RawRecord Creation
#       │
#       ▼
# Candidate Matching & Deduplication
#       │
#       ▼
# Canonical Candidate Profile
#       │
#       ▼
# Projection (Config Driven)
#       │
#       ▼
# Validation
#       │
#       ▼
# Final Output
# """
#     )

#     # ============================================================
#     # STEP 1
#     # ============================================================

#     print("=" * 70)
#     print("STEP 1 : INGEST STRUCTURED CSV DATA")
#     print("=" * 70)

#     records = ingest_csv(csv_path)

#     print(f"✓ Loaded {len(records)} candidate records from CSV.\n")

#     # ============================================================
#     # STEP 2
#     # ============================================================

#     print("=" * 70)
#     print("STEP 2 : INGEST UNSTRUCTURED RESUME PDFs")
#     print("=" * 70)

#     resume_dir = Path(resume_folder)

#     resume_count = 0

#     for pdf in resume_dir.glob("resume_*.pdf"):
#         records.append(ingest_resume(str(pdf)))
#         resume_count += 1

#     print(f"✓ Parsed {resume_count} resume(s).")
#     print(f"✓ Total raw records available: {len(records)}\n")

#     # ============================================================
#     # STEP 3
#     # ============================================================

#     print("=" * 70)
#     print("STEP 3 : MATCH & MERGE CANDIDATES")
#     print("=" * 70)

#     profiles = merge_all(records)

#     print(f"\n✓ Created {len(profiles)} canonical candidate profiles.\n")

#     # ============================================================
#     # STEP 4
#     # ============================================================

#     print("=" * 70)
#     print("STEP 4 : LOAD PROJECTION CONFIGURATION")
#     print("=" * 70)

#     config = load_projection_config()

#     print("✓ Projection configuration loaded.\n")

#     # ============================================================
#     # STEP 5
#     # ============================================================

#     print("=" * 70)
#     print("STEP 5 : PROJECT OUTPUT")
#     print("=" * 70)

#     projected_profiles = []

#     for profile in profiles:
#         projected_profiles.append(project_profile(profile, config))

#     print(f"✓ Projected {len(projected_profiles)} profiles.\n")

#     # ============================================================
#     # STEP 6
#     # ============================================================

#     print("=" * 70)
#     print("STEP 6 : VALIDATE PROJECTED OUTPUT")
#     print("=" * 70)

#     final_profiles = []

#     passed = 0
#     failed = 0

#     for profile in projected_profiles:

#         valid, errors = validate_profile(profile, config)

#         if valid:
#             passed += 1
#             final_profiles.append(profile)
#         else:
#             failed += 1

#             print(f"\nValidation failed for {profile.get('candidate_id')}")

#             for err in errors:
#                 print("   -", err)

#     print(f"\n✓ Passed : {passed}")
#     print(f"✓ Failed : {failed}")

#     print("\nPipeline execution completed successfully.\n")

#     return final_profiles


# if __name__ == "__main__":

#     import json

#     csv_path = "sample_inputs/recruiter.csv"
#     resume_folder = "sample_inputs"

#     results = run_pipeline(
#         csv_path=csv_path,
#         resume_folder=resume_folder,
#     )

#     print("=" * 70)
#     print("FINAL PROJECTED CANDIDATE PROFILES")
#     print("=" * 70)

#     for profile in results:
#         print(json.dumps(profile, indent=2))
#         print("-" * 70)

#     print("\nSUMMARY")
#     print("=" * 70)
#     print(f"Final Candidate Profiles : {len(results)}")
#     print("Validation Status        : PASSED")
#     print("Pipeline Status          : SUCCESS")
#     print("=" * 70)
"""
End-to-end candidate transformation pipeline.

Flow:
CSV + Resume(s)
        ↓
Raw Records
        ↓
Merge (Match + Conflict Resolution + Confidence)
        ↓
Canonical CandidateProfiles
        ↓
Projection (Config Driven)
        ↓
Validation
        ↓
Final Output
"""

from pathlib import Path

from src.ingest_csv import ingest_csv
from src.ingest_resume import ingest_resume
from src.merge import merge_all
from src.project import load_projection_config, project_profile
from src.validate import validate_profile


def run_pipeline(
    csv_path: str,
    resume_folder: str,
    output_config: dict = None,
) -> list[dict]:
    """
    Runs the complete pipeline end-to-end.

    Args:
        csv_path:      Path to recruiter CSV file.
        resume_folder: Folder containing resume_*.pdf files.
        output_config: Optional runtime config dict for custom projection.
                       If None, uses the default full canonical schema.

    Returns:
        List of validated projected profile dicts (ready for JSON output).
    """

    print("\n" + "=" * 70)
    print("     EIGHTFOLD CANDIDATE TRANSFORMATION PIPELINE")
    print("=" * 70)

    # ----------------------------------------------------------------
    # STEP 1 — Ingest structured CSV
    # ----------------------------------------------------------------
    print("\n[Step 1] Ingesting structured CSV data...")
    records = ingest_csv(csv_path)
    print(f"  ✓ Loaded {len(records)} record(s) from CSV: {csv_path}")

    # ----------------------------------------------------------------
    # STEP 2 — Ingest unstructured resume PDFs
    # ----------------------------------------------------------------
    print("\n[Step 2] Ingesting unstructured resume PDFs...")
    resume_dir = Path(resume_folder)
    resume_count = 0

    for pdf in sorted(resume_dir.glob("resume_*.pdf")):
        record = ingest_resume(str(pdf))
        records.append(record)
        resume_count += 1
        print(f"  ✓ Parsed: {pdf.name}")

    if resume_count == 0:
        print(f"  ⚠ No resume_*.pdf files found in: {resume_folder}")

    print(f"  ✓ Total raw records: {len(records)}")

    # ----------------------------------------------------------------
    # STEP 3 — Match + Merge candidates
    # ----------------------------------------------------------------
    print("\n[Step 3] Matching and merging candidates...")
    profiles = merge_all(records)
    print(f"  ✓ {len(records)} raw records → {len(profiles)} canonical profile(s)")

    # ----------------------------------------------------------------
    # STEP 4 — Load projection config
    # ----------------------------------------------------------------
    print("\n[Step 4] Loading projection config...")
    config = load_projection_config(output_config)

    if output_config is None:
        print("  ✓ No custom config provided — using default full schema")
    else:
        field_names = [f["path"] for f in output_config.get("fields", [])]
        print(f"  ✓ Custom config loaded — fields: {field_names}")
        print(f"  ✓ include_confidence : {output_config.get('include_confidence', True)}")
        print(f"  ✓ include_provenance : {output_config.get('include_provenance', True)}")
        print(f"  ✓ on_missing         : {output_config.get('on_missing', 'null')}")

    # ----------------------------------------------------------------
    # STEP 5 — Project profiles
    # ----------------------------------------------------------------
    print("\n[Step 5] Projecting profiles...")
    projected_profiles = []

    for profile in profiles:
        try:
            projected = project_profile(profile, config)
            projected_profiles.append(projected)
        except ValueError as e:
            # on_missing = "error" raised — log and skip this profile
            print(f"  ✗ Projection error for {profile.candidate_id}: {e}")

    print(f"  ✓ Projected {len(projected_profiles)} profile(s)")

    # ----------------------------------------------------------------
    # STEP 6 — Validate projected output
    # ----------------------------------------------------------------
    print("\n[Step 6] Validating projected output...")
    final_profiles = []
    passed = 0
    failed = 0

    for profile in projected_profiles:
        valid, errors = validate_profile(profile, config)
        if valid:
            passed += 1
            final_profiles.append(profile)
        else:
            failed += 1
            cid = profile.get("candidate_id", "unknown")
            print(f"  ✗ Validation failed for {cid}:")
            for err in errors:
                print(f"      - {err}")

    print(f"  ✓ Passed: {passed}  |  Failed: {failed}")

    # ----------------------------------------------------------------
    # Done
    # ----------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  Pipeline complete.")
    print(f"  Final profiles ready: {len(final_profiles)}")
    print("=" * 70 + "\n")

    return final_profiles


if __name__ == "__main__":
    import json

    results = run_pipeline(
        csv_path="sample_inputs/recruiter.csv",
        resume_folder="sample_inputs",
        output_config=None,  # use default schema
    )

    print("=" * 70)
    print("FINAL PROFILES")
    print("=" * 70)
    for profile in results:
        print(json.dumps(profile, indent=2))
        print("-" * 70)

    print(f"\nTotal: {len(results)} profile(s)")