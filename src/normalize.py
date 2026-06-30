"""
Normalization functions: phone -> E.164, skills -> canonical names,
dates -> YYYY-MM. Used after ingestion, before merging.
"""

import re
import phonenumbers
from phonenumbers import NumberParseException

# Default region used when a phone number has no country code.
# Per design doc: configurable, defaults to IN.
DEFAULT_REGION = "IN"

# Canonical skill name lookup — extend this as needed.
SKILL_SYNONYMS = {
    "js": "JavaScript",
    "javascript": "JavaScript",
    "py": "Python",
    "python": "Python",
    "sql": "SQL",
    "aws": "AWS",
    "docker": "Docker",
    "ts": "TypeScript",
    "typescript": "TypeScript",
}


def normalize_phone(raw: str, region: str = DEFAULT_REGION) -> str | None:
    """Converts a raw phone string to E.164 format. Returns None if unparseable."""
    if not raw:
        return None
    try:
        parsed = phonenumbers.parse(raw, region)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except NumberParseException:
        pass
    return None


def normalize_skill(raw: str) -> str:
    """Maps a raw skill string to its canonical name; falls back to title-cased input."""
    key = raw.strip().lower()
    return SKILL_SYNONYMS.get(key, raw.strip())


def normalize_skills(raw_list: list[str]) -> list[str]:
    seen = []
    for s in raw_list:
        canon = normalize_skill(s)
        if canon not in seen:
            seen.append(canon)
    return seen


# Matches things like "Jan 2022", "January 2022", "2022-01", "2022"
MONTH_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}

DATE_TEXT_RE = re.compile(r"([A-Za-z]{3,9})\s+(\d{4})")
DATE_ISO_RE = re.compile(r"(\d{4})-(\d{2})")
YEAR_ONLY_RE = re.compile(r"^(\d{4})$")


def normalize_date(raw: str) -> str | None:
    """Converts free-text or partial dates into YYYY-MM. Returns None if unparseable
    or if the value indicates an ongoing/current period (caller should treat as None=present)."""
    if not raw:
        return None
    raw = raw.strip()

    if raw.lower() in ("present", "current", "ongoing", "now"):
        return None

    m = DATE_ISO_RE.match(raw)
    if m:
        return f"{m.group(1)}-{m.group(2)}"

    m = DATE_TEXT_RE.match(raw)
    if m:
        month_str, year = m.group(1).lower()[:3], m.group(2)
        month_num = MONTH_MAP.get(month_str)
        if month_num:
            return f"{year}-{month_num}"

    m = YEAR_ONLY_RE.match(raw)
    if m:
        return f"{m.group(1)}-01"  # default to January if only year given

    return None


if __name__ == "__main__":
    # Quick manual sanity checks
    print(normalize_phone("9876543210"))          # expect +91...
    print(normalize_phone("+91 9876543210"))       # expect +91...
    print(normalize_phone("not-a-phone"))          # expect None
    print(normalize_skills(["JS", "python", "AWS", "Python"]))
    print(normalize_date("Jan 2022"))               # expect 2022-01
    print(normalize_date("2022-01"))                # expect 2022-01
    print(normalize_date("Present"))                # expect None