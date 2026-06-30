# Eightfold Candidate Transformation Pipeline

## Overview

This project implements an end-to-end candidate data transformation pipeline for the Eightfold AI Software Engineering Assignment.

The pipeline ingests candidate information from multiple heterogeneous sources (structured CSV and unstructured Resume PDFs), normalizes the data, identifies duplicate candidate profiles, merges them into a canonical representation, assigns confidence scores, tracks provenance, and finally produces configurable output through a runtime projection configuration.

The guiding principle followed throughout the implementation is:

> **"Wrong-but-confident is worse than honestly-empty."**

---

# Project Workflow

```
                 CSV Recruiter Data
                        │
                        ▼
                CSV Ingestion
                        │
                        ▼
                 Resume PDFs
                        │
                        ▼
              Resume Ingestion
                        │
                        ▼
                Raw Candidate Records
                        │
                        ▼
                Data Normalization
                        │
                        ▼
        Candidate Matching & Deduplication
                        │
                        ▼
           Canonical Candidate Profile
                        │
                        ▼
            Configurable Projection
                        │
                        ▼
                  Output Validation
                        │
                        ▼
                 Final JSON Output
```

---

# Project Structure

```
eightfold-candidate-transformer/

│
├── src/
│   ├── schema.py
│   ├── ingest_csv.py
│   ├── ingest_resume.py
│   ├── normalize.py
│   ├── merge.py
│   ├── project.py
│   ├── validate.py
│   └── pipeline.py
│
├── config/
│   └── example_config.json
│
├── sample_inputs/
│   ├── recruiter.csv
│   ├── resume_bushra.pdf
│   ├── resume_aman.pdf
│   ├── ...
│
├── cli.py
├── requirements.txt
└── README.md
```

---

# Pipeline Stages

## 1. Data Ingestion

### Structured Source

- Recruiter CSV

### Unstructured Source

- Resume PDF

Both sources are converted into a common `RawRecord` representation.

---

## 2. Normalization

The normalization stage standardizes:

- Emails
- Phone numbers (E.164)
- Dates
- Skills

---

## 3. Candidate Matching

Candidates are matched using strong identifiers.

Priority order:

1. Email
2. Phone Number
3. GitHub URL (future)
4. LinkedIn URL (future)

Weak matching:

- Name + Company

Contradiction rule:

If two records contain conflicting strong identifiers (email or phone), they are **not merged**.

---

## 4. Candidate Merge

Matching records are merged into one canonical candidate profile.

Rules:

- Highest-priority value wins for scalar fields.
- Array fields are unioned.
- Skills are deduplicated.
- Provenance is preserved.
- Confidence scores are calculated.

---

## 5. Projection

The final output is controlled through:

```
config/example_config.json
```

The configuration supports:

- Selecting output fields
- Renaming fields
- Hiding confidence
- Hiding provenance
- Missing value handling

No code changes are required.

---

## 6. Validation

The projected output is validated against the runtime configuration.

Validation checks include:

- Required fields
- Unexpected fields
- Confidence score range
- Projection correctness

---

# Matching Strategy

Strong Matches

- Email
- Phone Number
- GitHub (future)
- LinkedIn (future)

Weak Matches

- Name + Company

Profiles with conflicting strong identifiers are intentionally kept separate.

---

# Confidence Scoring

Confidence depends on:

- Source reliability
- Number of corroborating sources
- Identity match strength
- Completeness of profile

Confidence values range between:

```
0.0 – 1.0
```

---

# Provenance

Every merged field records:

- Source
- Merge method

Example

```json
{
    "field":"skills.Python",
    "source":"resume",
    "method":"union"
}
```

---

# Running the Project

Install dependencies

```bash
pip install -r requirements.txt
```

Run with default schema (full canonical output)

```bash
python cli.py
```

Run with custom config (renamed fields, no provenance — the required twist)

```bash
python cli.py --config config/example_config.json
```

Run with all options

```bash
python cli.py \
  --csv sample_inputs/recruiter.csv \
  --resume sample_inputs \
  --config config/example_config.json \
  --output output/profiles.json
```

Run pipeline directly

```bash
python -m src.pipeline
```

Run tests

```bash
python -m pytest tests/ -v
```

# Sample Output

The pipeline generates canonical candidate profiles with:

- Normalized data
- Merged information
- Confidence scores
- Provenance
- Configurable output

---

# Assumptions

- Resume PDFs follow a reasonably consistent format.
- CSV data may contain missing values.
- Email and phone are treated as strong identifiers.
- Missing strong identifiers are never assumed to match.
- Wrong merges are avoided even if it results in duplicate profiles.

---

# Future Improvements

- LinkedIn ingestion
- GitHub ingestion
- ATS JSON ingestion
- OCR support
- Semantic resume parsing using LLMs
- Embedding-based candidate similarity

---

# Technologies Used

- Python
- Pydantic
- pandas
- pdfplumber
- phonenumbers

---