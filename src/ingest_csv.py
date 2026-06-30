"""
Reads a recruiter CSV export and converts each row into a RawRecord.
"""

import pandas as pd
from src.schema import RawRecord


def ingest_csv(filepath: str) -> list[RawRecord]:
    """
    Reads a CSV file with columns: name, email, phone, current_company, title
    Returns a list of RawRecord objects (one per row).
    Missing/garbage values become None rather than crashing.
    """
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        print(f"[ingest_csv] Failed to read {filepath}: {e}")
        return []

    records = []
    for idx, row in df.iterrows():
        # .get-style safe access with NaN handling
        def safe(col):
            val = row.get(col)
            if pd.isna(val) or val == "":
                return None
            return str(val).strip()

        name = safe("name")
        email = safe("email")
        phone = safe("phone")
        company = safe("current_company")
        title = safe("title")

        record = RawRecord(
            source_type="csv",
            source_id=f"{filepath}:row{idx}",
            full_name=name,
            emails=[email] if email else [],
            phones=[phone] if phone else [],
            company=company,
            title=title,
        )
        records.append(record)

    return records


if __name__ == "__main__":
    # Quick manual test when running this file directly
    results = ingest_csv("sample_inputs/recruiter.csv")
    for r in results:
        print(r)