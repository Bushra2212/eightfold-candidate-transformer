"""
Canonical schema for the unified candidate profile.
Every source gets mapped into this structure before merging.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class Location(BaseModel):
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None  # ISO-3166 alpha-2


class Links(BaseModel):
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    other: List[str] = Field(default_factory=list)


class Skill(BaseModel):
    name: str
    confidence: float
    sources: List[str] = Field(default_factory=list)


class Experience(BaseModel):
    company: Optional[str] = None
    title: Optional[str] = None
    start: Optional[str] = None  # YYYY-MM
    end: Optional[str] = None    # YYYY-MM or None if current
    summary: Optional[str] = None


class Education(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    field: Optional[str] = None
    end_year: Optional[int] = None


class ProvenanceEntry(BaseModel):
    field: str          # which field this provenance entry describes
    source: str          # e.g. "csv", "resume"
    method: str           # e.g. "direct", "regex_extraction"


class CandidateProfile(BaseModel):
    candidate_id: str
    full_name: Optional[str] = None
    emails: List[str] = Field(default_factory=list)
    phones: List[str] = Field(default_factory=list)
    location: Location = Field(default_factory=Location)
    links: Links = Field(default_factory=Links)
    headline: Optional[str] = None
    years_experience: Optional[float] = None
    skills: List[Skill] = Field(default_factory=list)
    experience: List[Experience] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    provenance: List[ProvenanceEntry] = Field(default_factory=list)
    overall_confidence: float = 0.0


# A lightweight "raw record" type — what each source's ingester produces
# BEFORE normalization/merging. Looser typing on purpose (everything optional,
# strings instead of structured types) because raw extraction is messy.
class RawRecord(BaseModel):
    source_type: str          # "csv", "github", etc.
    source_id: str            # filename or identifier
    full_name: Optional[str] = None
    emails: List[str] = Field(default_factory=list)
    phones: List[str] = Field(default_factory=list)
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    headline: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    skills_raw: List[str] = Field(default_factory=list)
    experience_raw: List[dict] = Field(default_factory=list)
    education_raw: List[dict] = Field(default_factory=list)
    raw_text: Optional[str] = None  # for resume/notes, keep raw text around