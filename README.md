# Eightfold Candidate Transformation Pipeline

## Overview

This project implements an end-to-end candidate data transformation pipeline for the **Eightfold AI Software Engineering Assignment**.

The pipeline ingests candidate information from multiple heterogeneous sources (**structured CSV** and **unstructured Resume PDFs**), normalizes the data, identifies duplicate candidate profiles, merges them into a canonical representation, assigns confidence scores, tracks provenance, and finally produces configurable output through a runtime projection configuration.

---

## Design Principle

> **"Wrong-but-confident is worse than honestly-empty."**

The pipeline prioritizes avoiding **false-positive merges** over aggressively combining uncertain candidate records. When strong identity evidence is unavailable, the system preserves separate candidate profiles rather than risking an incorrect merge.

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
│   ├── resume_rohan.pdf
│   ├── resume_priya.pdf
│   ├── resume_karan.pdf
│   └── resume_neha.pdf
│
├── tests/
│   ├── test_merge.py
│   └── test_pipeline.py
│
├── output/
│   └── profiles.json
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

Both sources are converted into a common **RawRecord** representation.

---

## 2. Normalization

The normalization stage standardizes:

- Emails
- Phone numbers (E.164 format)
- Dates
- Skills

This ensures consistent candidate information across heterogeneous sources.

---

## 3. Candidate Matching

Candidates are matched using strong identity signals.

### Strong Matches

- Email
- Phone Number
- GitHub URL *(future)*
- LinkedIn URL *(future)*

### Weak Matches

- Name + Company
- Name + Company + Role

Weak matches receive a **low confidence score** and are merged **only if their confidence exceeds the configured match threshold**.

### Contradiction Rule

If two records contain conflicting strong identifiers (email or phone), they are intentionally **not merged**.

---

## 4. Candidate Merge

Matching records are merged into a single canonical candidate profile.

Merge rules:

- Highest-priority value wins for scalar fields
- Array fields are unioned
- Skills are deduplicated
- Provenance is preserved
- Confidence scores are calculated

---

## 5. Configurable Projection

The pipeline first builds a complete canonical candidate profile.

A runtime configuration file:

```
config/example_config.json
```

controls the final output schema.

Supported configuration options include:

- Selecting output fields
- Renaming fields
- Hiding confidence scores
- Hiding provenance
- Missing-value handling

Different output schemas can therefore be produced **without modifying the source code**, satisfying the configurable output requirement of the assignment.

---

## 6. Validation

The projected output is validated against the runtime configuration.

Validation checks include:

- Required fields
- Unexpected fields
- Confidence score range
- Projection correctness

Only valid projected profiles are returned.

---

# Matching Strategy

## Strong Matches

- Email
- Phone Number
- GitHub *(future)*
- LinkedIn *(future)*

## Weak Matches

- Name + Company
- Name + Company + Role

Weak matches receive a low confidence score and are considered only when their confidence satisfies the configured merge threshold.

Profiles with conflicting strong identifiers are intentionally kept separate to minimize false merges.

---

# Confidence Scoring

Confidence depends on multiple factors, including:

- Source reliability
- Number of corroborating sources
- Identity match strength
- Completeness of profile

Confidence values range between:

```
0.0 – 1.0
```

Higher confidence indicates stronger evidence that the merged profile correctly represents a single candidate.

---

# Provenance

Every merged field records:

- Source
- Merge method

Example:

```json
{
  "field": "skills.Python",
  "source": "resume",
  "method": "union"
}
```

This provides full traceability of every value in the canonical profile.

---

# Running the Project

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Run with Default Configuration

```bash
python cli.py
```

---

## Run with Custom Projection Configuration

```bash
python cli.py --config config/example_config.json
```

---

## Run with All Options

```bash
python cli.py --csv sample_inputs/recruiter.csv --resume sample_inputs --config config/example_config.json --output output/profiles.json
```

---

## Run Pipeline Directly

```bash
python -m src.pipeline
```

---

# Testing

Run all automated tests:

```bash
python -m pytest tests/ -v
```

The project includes **19 automated tests** covering:

- Phone normalization
- Date normalization
- Skill normalization
- Candidate matching
- Merge logic
- Contradiction handling
- Confidence scoring
- End-to-end pipeline execution
- Configurable projection

All tests currently pass successfully.

---

# Sample Output

The pipeline generates canonical candidate profiles containing:

- Normalized data
- Merged information
- Confidence scores
- Provenance
- Configurable output schema

A sample generated output is available in:

```
output/profiles.json
```

---

# Assumptions

- Resume PDFs follow a reasonably consistent format.
- CSV data may contain missing values.
- Email and phone are treated as strong identifiers.
- Weak matches receive low confidence and are filtered using a configurable threshold.
- Missing strong identifiers are never assumed to represent the same candidate.
- False-positive merges are avoided even if this results in duplicate candidate profiles.

---

# Future Improvements

- LinkedIn ingestion
- GitHub ingestion
- ATS JSON ingestion
- OCR support for scanned resumes
- Semantic resume parsing using LLMs
- Embedding-based candidate similarity
- Active learning for merge threshold tuning

---

# Technologies Used

- Python
- Pydantic
- pandas
- pdfplumber
- phonenumbers
- pytest

---

# License

This project was developed as part of the **Eightfold AI Software Engineering Assignment** and is intended for evaluation purposes.
