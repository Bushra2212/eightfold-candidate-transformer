"""
Reads a resume PDF and extracts candidate info using text patterns.
Unstructured source — no fixed fields, so we use regex/heuristics.
"""

import re
import pdfplumber
from src.schema import RawRecord
from src.normalize import normalize_date


EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(\+?\d[\d\-\s]{8,14}\d)")
SKILLS_HEADER_RE = re.compile(r"^skills$", re.IGNORECASE)
EXPERIENCE_HEADER_RE = re.compile(r"^experience$", re.IGNORECASE)
LOCATION_LINE_RE = re.compile(r"location:\s*(.+)", re.IGNORECASE)

# Matches lines like: "Software Engineer, TechCorp, Jan 2022 - Present"
EXPERIENCE_LINE_RE = re.compile(
    r"^(.+?),\s*(.+?),\s*([A-Za-z]+\s+\d{4}|\d{4})\s*-\s*(Present|Current|[A-Za-z]+\s+\d{4}|\d{4})$",
    re.IGNORECASE
)


def extract_text(filepath: str) -> str:
    text = ""
    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"[ingest_resume] Failed to read {filepath}: {e}")
    return text


def extract_name(text: str) -> str | None:
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if lines:
        first_line = lines[0]
        if len(first_line) < 50 and "@" not in first_line and not any(c.isdigit() for c in first_line):
            return first_line
    return None


def extract_skills(text: str) -> list[str]:
    lines = [l.strip() for l in text.split("\n")]
    for i, line in enumerate(lines):
        if SKILLS_HEADER_RE.match(line):
            for next_line in lines[i + 1:]:
                if next_line.strip():
                    return [s.strip() for s in next_line.split(",") if s.strip()]
    return []


def extract_location(text: str) -> tuple[str | None, str | None, str | None]:
    """
    Looks for a 'Location: City, Region, Country' style line.
    Returns (city, region, country) — country left as free text here;
    ISO-3166 conversion happens at normalize/merge time, not extraction time,
    keeping this layer a pure "what does the text say" extractor.
    """
    m = LOCATION_LINE_RE.search(text)
    if not m:
        return None, None, None
    parts = [p.strip() for p in m.group(1).split(",")]
    city = parts[0] if len(parts) > 0 and parts[0] else None
    region = parts[1] if len(parts) > 1 and parts[1] else None
    country = parts[2] if len(parts) > 2 and parts[2] else None
    return city, region, country


def extract_experience(text: str) -> list[dict]:
    """
    Parses lines under an 'Experience' header matching the pattern:
    'Title, Company, StartDate - EndDate'
    Dates are normalized to YYYY-MM here (None for 'Present'/'Current').
    Returns a list of dicts (kept as raw dicts in RawRecord.experience_raw;
    merge.py is responsible for turning these into Experience objects).
    """
    lines = [l.strip() for l in text.split("\n")]
    entries = []
    in_experience_section = False

    for line in lines:
        if EXPERIENCE_HEADER_RE.match(line):
            in_experience_section = True
            continue
        if not in_experience_section:
            continue
        # Stop once we hit the next section header (e.g. "Skills")
        if SKILLS_HEADER_RE.match(line) or EDUCATION_HEADER_RE.match(line) if False else False:
            break

        m = EXPERIENCE_LINE_RE.match(line)
        if m:
            title, company, start_raw, end_raw = m.groups()
            entries.append({
                "title": title.strip(),
                "company": company.strip(),
                "start": normalize_date(start_raw),
                "end": normalize_date(end_raw),  # normalize_date returns None for "Present"/"Current" too
            })
        elif line == "" or SKILLS_HEADER_RE.match(line):
            # blank line or next section reached — stop parsing experience
            if entries:
                break

    return entries


def ingest_resume(filepath: str) -> RawRecord:
    text = extract_text(filepath)

    if not text.strip():
        return RawRecord(
            source_type="resume",
            source_id=filepath,
            raw_text=None,
        )

    emails = EMAIL_RE.findall(text)
    phones = PHONE_RE.findall(text)
    name = extract_name(text)
    skills = extract_skills(text)
    city, region, country = extract_location(text)
    experience = extract_experience(text)

# Use the most recent experience (first entry) as the current role/company
    company = None
    title = None

    if experience:
        title = experience[0]["title"]
        company = experience[0]["company"]

    record = RawRecord(
    source_type="resume",
    source_id=filepath,
    full_name=name,
    emails=list(dict.fromkeys(emails)),
    phones=list(dict.fromkeys(p.strip() for p in phones)),
    city=city,
    region=region,
    country=country,
    company=company,
    title=title,
    skills_raw=skills,
    experience_raw=experience,
    raw_text=text,
)
    return record


if __name__ == "__main__":
    from pathlib import Path

    for pdf in sorted(Path("sample_inputs").glob("resume_*.pdf")):
        print(f"\n{'='*60}")
        print(pdf.name)
        print("="*60)

        result = ingest_resume(str(pdf))
        print(result.model_dump_json(indent=2))