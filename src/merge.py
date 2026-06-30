"""
Merges RawRecords from multiple sources into unified CandidateProfiles.
Implements the matching + conflict-resolution + confidence policy
from the design doc (Section 3).

Matching policy: explicit OR-rules on primary-key-style identifiers,
with a contradiction veto protecting a weaker fallback rule.

  MATCH if ANY of:
    - email matches
    - phone matches
    - github_url matches
    - linkedin_url matches

  ELSE IF none of the above match AND none of the above CONTRADICT:
    - name + company match -> weak merge allowed
      (if role/title also matches, this is noted as extra corroboration
       and reflected in confidence scoring, but role is NEVER required)
"""

# import profile
# from tokenize import group

from src.schema import RawRecord, CandidateProfile, Skill, ProvenanceEntry, Experience
from src.normalize import normalize_phone, normalize_skills, normalize_date

# Source priority tiers — higher number = more trusted.
SOURCE_PRIORITY = {
    "csv": 3,
    "ats_json": 3,
    "resume": 2,
    "github": 1,
    "notes": 1,
}
# Minimum confidence required to merge two records
MATCH_THRESHOLD = 0.80
# Base confidence per source tier (design doc Section 3).
SOURCE_BASE_CONFIDENCE = {
    "csv": 0.9,
    "ats_json": 0.9,
    "resume": 0.7,
    "github": 0.5,
    "notes": 0.5,
}


def _norm(s: str | None) -> str | None:
    if not s:
        return None
    return s.strip().lower()


def _phone_digits(p: str | None) -> str | None:
    if not p:
        return None
    digits = "".join(c for c in p if c.isdigit())
    return digits[-10:] if len(digits) >= 10 else digits or None


def _has_contradiction(a: RawRecord, b: RawRecord) -> bool:
    """
    Checks for HARD contradictions between two records.

    Design decision:
    ----------------
    Different email addresses or phone numbers are NOT considered
    contradictions because a candidate may legitimately have multiple
    emails (personal/work) or multiple phone numbers.

    GitHub and LinkedIn URLs are treated as strong identity identifiers.
    If both records contain one of these and the values differ, we
    consider them different people.

    Missing values never count as contradictions.
    """

    # GitHub contradiction
    github_a = _norm(getattr(a, "github_url", None))
    github_b = _norm(getattr(b, "github_url", None))

    if github_a and github_b and github_a != github_b:
        return True

    # LinkedIn contradiction
    linkedin_a = _norm(getattr(a, "linkedin_url", None))
    linkedin_b = _norm(getattr(b, "linkedin_url", None))

    if linkedin_a and linkedin_b and linkedin_a != linkedin_b:
        return True

    return False


def _is_match(a: RawRecord, b: RawRecord) -> tuple[bool, str | None, float]:
    """
    Checks the explicit OR-rules between two records, with a contradiction
    veto protecting the weaker name+company fallback rule.
    Returns (matched: bool, reason: str | None, confidence: float).
    """

    # Rule 1: email match
    emails_a = {_norm(e) for e in a.emails if e}
    emails_b = {_norm(e) for e in b.emails if e}
    if emails_a and emails_b and emails_a & emails_b:
        return True, "email_match", 0.95

    # Rule 2: phone match
    phones_a = {_phone_digits(p) for p in a.phones if p}
    phones_b = {_phone_digits(p) for p in b.phones if p}
    phones_a.discard(None)
    phones_b.discard(None)
    if phones_a and phones_b and phones_a & phones_b:
        return True, "phone_match", 0.90

    # Rule 3: GitHub URL match
    github_a = _norm(getattr(a, "github_url", None))
    github_b = _norm(getattr(b, "github_url", None))
    if github_a and github_b and github_a == github_b:
        return True, "github_url_match", 0.98

    # Rule 4: LinkedIn URL match
    linkedin_a = _norm(getattr(a, "linkedin_url", None))
    linkedin_b = _norm(getattr(b, "linkedin_url", None))
    if linkedin_a and linkedin_b and linkedin_a == linkedin_b:
        return True, "linkedin_url_match",0.98

    # Veto: if a strong identifier explicitly contradicts, never fall
    # through to the weaker name+company rule below.
    if _has_contradiction(a, b):
        return False, None, 0.0

    name_a, name_b = _norm(a.full_name), _norm(b.full_name)
    company_a, company_b = _norm(a.company), _norm(b.company)

    if (
    name_a and name_b and
    name_a == name_b and
    company_a and company_b and
    company_a == company_b
    ):
        emails_a = {_norm(e) for e in a.emails if e}
        emails_b = {_norm(e) for e in b.emails if e}

        phones_a = {_phone_digits(p) for p in a.phones if p}
        phones_b = {_phone_digits(p) for p in b.phones if p}
        phones_a.discard(None)
        phones_b.discard(None)

        email_conflict = (
        emails_a and emails_b and
        not (emails_a & emails_b)
        )

        phone_conflict = (
        phones_a and phones_b and
        not (phones_a & phones_b)
        )
        # Do not merge if NEITHER record has any primary-key identifier at all
        # (no email, no phone on both sides = insufficient evidence)
        has_any_identifier_a = bool(emails_a or phones_a)
        has_any_identifier_b = bool(emails_b or phones_b)
        if not has_any_identifier_a and not has_any_identifier_b:
            return False, None, 0.0

    # If BOTH strong identifiers disagree,
    # do NOT use the weak fallback.
        if email_conflict and phone_conflict:
            return False, None, 0.0

        title_a, title_b = _norm(a.title), _norm(b.title)

        if title_a and title_b and title_a == title_b:
            return True, "name_company_role_match",0.45

        return True, "name_and_company_match", 0.40
    return False, None, 0.0


def match_records(records: list[RawRecord]) -> tuple[list[list[RawRecord]], dict[int, list[str]]]:
    """
    Groups raw records that likely refer to the same candidate, using the
    explicit OR-rule policy in _is_match(). Union-Find grouping ensures
    transitive merges. Also returns the set of match reasons per group,
    used for confidence scoring and demo transparency.
    """
    n = len(records)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    match_log = []
    pair_reasons: list[tuple[int, int, str]] = []

    for i in range(n):
        for j in range(i + 1, n):
            matched, reason, score = _is_match(records[i], records[j])
            if matched and score >= MATCH_THRESHOLD:
                union(i, j)
                pair_reasons.append((i, j, reason))
                match_log.append(
                    (
                        records[i].source_id,
                        records[j].source_id,
                        f"{reason} (confidence={score:.2f})"
                    )
                )

    groups: dict[int, list[RawRecord]] = {}
    for idx, rec in enumerate(records):
        root = find(idx)
        groups.setdefault(root, []).append(rec)

    group_reasons: dict[int, list[str]] = {}
    for i, j, reason in pair_reasons:
        root = find(i)
        group_reasons.setdefault(root, []).append(reason)

    if match_log:
        print("[match_records] Merge decisions:")
        for a_id, b_id, reason in match_log:
            print(f"  {a_id}  <->  {b_id}   (matched on: {reason})")

    group_keys = list(groups.keys())
    final_groups = [groups[k] for k in group_keys]
    final_reasons = {i: group_reasons.get(root, []) for i, root in enumerate(group_keys)}

    return final_groups, final_reasons


def _pick_winner(values_with_source: list[tuple[str, str]]) -> tuple[str, str] | None:
    """
    Picks a winner by source priority, with later-in-list = more recent
    as the tiebreaker among equal-priority sources.
    """
    if not values_with_source:
        return None
    best = None
    best_priority = -1
    for value, source in values_with_source:
        priority = SOURCE_PRIORITY.get(source, 0)
        if priority >= best_priority:
            best = (value, source)
            best_priority = priority
    return best


def merge_group(group: list[RawRecord], candidate_id: str, match_reasons: list[str] | None = None) -> CandidateProfile:
    """Merges one group of RawRecords (same candidate) into a single CandidateProfile."""

    match_reasons = match_reasons or []
    profile = CandidateProfile(candidate_id=candidate_id)
    provenance: list[ProvenanceEntry] = []

    # --- full_name ---
    name_candidates = [(r.full_name, r.source_type) for r in group if r.full_name]
    winner = _pick_winner(name_candidates)
    if winner:
        profile.full_name = winner[0]
        provenance.append(ProvenanceEntry(field="full_name", source=winner[1], method="direct"))

    # --- emails: union, normalized ---
    all_emails = []
    email_sources = []
    for r in group:
        for e in r.emails:
            norm = e.strip().lower()
            if norm and norm not in all_emails:
                all_emails.append(norm)
                email_sources.append(r.source_type)
    profile.emails = all_emails
    if email_sources:
        provenance.append(ProvenanceEntry(field="emails", source=",".join(set(email_sources)), method="union"))

    # --- phones: union, normalized to E.164 ---
    all_phones = []
    phone_sources = []
    for r in group:
        for p in r.phones:
            norm = normalize_phone(p)
            if norm and norm not in all_phones:
                all_phones.append(norm)
                phone_sources.append(r.source_type)
    profile.phones = all_phones
    if phone_sources:
        provenance.append(ProvenanceEntry(field="phones", source=",".join(set(phone_sources)), method="union"))
    # --- location: choose highest-priority non-empty values ---
    city_candidates = [(r.city, r.source_type) for r in group if r.city]
    region_candidates = [(r.region, r.source_type) for r in group if r.region]
    country_candidates = [(r.country, r.source_type) for r in group if r.country]

    city_winner = _pick_winner(city_candidates)
    region_winner = _pick_winner(region_candidates)
    country_winner = _pick_winner(country_candidates)

    if city_winner:
        profile.location.city = city_winner[0]
        provenance.append(
        ProvenanceEntry(
            field="location.city",
            source=city_winner[1],
            method="direct"
        )
    )

    if region_winner:
        profile.location.region = region_winner[0]
        provenance.append(
        ProvenanceEntry(
            field="location.region",
            source=region_winner[1],
            method="direct"
        )
    )

    if country_winner:
        profile.location.country = country_winner[0]
        provenance.append(
            ProvenanceEntry(
            field="location.country",
            source=country_winner[1],
            method="direct"
            )
        )

    # --- experience: company/title winner ---
    title_candidates = [(r.title, r.source_type) for r in group if r.title]
    company_candidates = [(r.company, r.source_type) for r in group if r.company]
    title_winner = _pick_winner(title_candidates)
    company_winner = _pick_winner(company_candidates)
    if title_winner or company_winner:
        profile.experience.append(Experience(
            company=company_winner[0] if company_winner else None,
            title=title_winner[0] if title_winner else None,
        ))
        if title_winner:
            provenance.append(ProvenanceEntry(field="experience.title", source=title_winner[1], method="direct"))
        if company_winner:
            provenance.append(ProvenanceEntry(field="experience.company", source=company_winner[1], method="direct"))

    # --- skills: union, canonicalized, with confidence ---
    skill_sources: dict[str, list[str]] = {}
    for r in group:
        for raw_skill in normalize_skills(r.skills_raw):
            skill_sources.setdefault(raw_skill, []).append(r.source_type)

    for skill_name, sources in skill_sources.items():
        base_conf = max(SOURCE_BASE_CONFIDENCE.get(s, 0.5) for s in sources)
        corroboration_bonus = 0.05 * (len(set(sources)) - 1)
        conf = min(base_conf + corroboration_bonus, 0.99)
        profile.skills.append(Skill(name=skill_name, confidence=round(conf, 2), sources=list(set(sources))))
        provenance.append(ProvenanceEntry(field=f"skills.{skill_name}", source=",".join(set(sources)), method="union"))

    
    
    profile.provenance = provenance
    # --- corroboration bonus ---
   
    # --- overall_confidence ---
    field_confidences = []
    if profile.full_name:
        field_confidences.append(SOURCE_BASE_CONFIDENCE.get(winner[1], 0.5) if winner else 0.5)
    if profile.emails:
        field_confidences.append(0.9)
    if profile.phones:
        field_confidences.append(0.85)
    if profile.experience:
        field_confidences.append(0.70)
    if profile.location.city:
        field_confidences.append(0.65)
    if profile.skills:
        field_confidences.append(0.75)
    # --- profile size bonus ---
    if len(group) == 1:
        field_confidences.append(0.40)
    elif len(group) == 2:
        field_confidences.append(0.60)
    else:
        field_confidences.append(0.90)
    for sk in profile.skills:
        field_confidences.append(sk.confidence)

    # Identity-match confidence, based on HOW this group was formed
    if any(r in ("email_match", "phone_match", "github_url_match", "linkedin_url_match") for r in match_reasons):
        field_confidences.append(0.95)
    elif "name_company_role_match" in match_reasons:
        field_confidences.append(0.75)
    elif "name_and_company_match" in match_reasons:
        field_confidences.append(0.55)

    profile.overall_confidence = round(
        sum(field_confidences) / len(field_confidences), 2
    ) if field_confidences else 0.0
    # Bonus for corroboration across multiple source types
    if len({r.source_type for r in group}) >= 2:
        profile.overall_confidence = min(profile.overall_confidence + 0.08, 0.99)

    # Penalty for a profile built from only one raw record
    if len(group) == 1:
        
        profile.overall_confidence = max(profile.overall_confidence - 0.20, 0.0)
    profile.overall_confidence = round(profile.overall_confidence, 2)
    return profile


def merge_all(records: list[RawRecord]) -> list[CandidateProfile]:
    """Top-level entry point: groups + merges all raw records into profiles."""
    groups, group_reasons = match_records(records)
    profiles = []
    for i, group in enumerate(groups):
        candidate_id = f"cand_{i+1:04d}"
        reasons = group_reasons.get(i, [])
        profiles.append(merge_group(group, candidate_id, reasons))
    return profiles


if __name__ == "__main__":
    from src.ingest_csv import ingest_csv
    from src.ingest_resume import ingest_resume
    resume_files = [
    "sample_inputs/resume_bushra.pdf",
    "sample_inputs/resume_aman.pdf",
    "sample_inputs/resume_rohan.pdf",
    "sample_inputs/resume_priya.pdf",
    "sample_inputs/resume_karan.pdf",
    "sample_inputs/resume_neha.pdf",
]
    resume_records = [ingest_resume(pdf) for pdf in resume_files]
    csv_records = ingest_csv("sample_inputs/recruiter.csv")
    all_records = csv_records + resume_records

    
    profiles = merge_all(all_records)

    print(f"\nTotal raw records: {len(all_records)} -> Merged into {len(profiles)} profiles\n")
    for p in profiles:
        print(p.model_dump_json(indent=2))
        print("---")