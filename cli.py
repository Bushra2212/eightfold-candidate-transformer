"""
Command-line interface for the Candidate Transformation Pipeline.

Usage examples:
  # Default run (uses sample inputs, no config)
  python cli.py

  # Custom sources
  python cli.py --csv sample_inputs/recruiter.csv --resume sample_inputs

  # With configurable output
  python cli.py --config config/example_config.json

  # Save output to file
  python cli.py --output output/profiles.json
"""

import argparse
import json
import os

from src.pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="Eightfold Multi-Source Candidate Data Transformer"
    )

    parser.add_argument(
        "--csv",
        default="sample_inputs/recruiter.csv",
        help="Path to recruiter CSV file (default: sample_inputs/recruiter.csv)",
    )

    parser.add_argument(
        "--resume",
        default="sample_inputs",
        help="Folder containing resume PDFs (default: sample_inputs/)",
    )

    parser.add_argument(
        "--config",
        default=None,
        help="Path to output config JSON file for custom projection (optional)",
    )

    parser.add_argument(
        "--output",
        default=None,
        help="Path to save output JSON file (optional — prints to terminal if not set)",
    )

    args = parser.parse_args()

    # Load config if provided
    output_config = None
    if args.config:
        if not os.path.exists(args.config):
            print(f"[cli] Config file not found: {args.config}")
            return
        with open(args.config, "r") as f:
            output_config = json.load(f)
        print(f"[cli] Loaded config: {args.config}")

    # Run pipeline
    profiles = run_pipeline(
        csv_path=args.csv,
        resume_folder=args.resume,
        output_config=output_config,
    )

    # Format output
    output_data = [p if isinstance(p, dict) else json.loads(p) for p in profiles]
    output_json = json.dumps(output_data, indent=2)

    # Print to terminal
    print("\nFINAL OUTPUT")
    print("=" * 70)
    print(output_json)
    print("=" * 70)
    print(f"\nTotal profiles: {len(profiles)}")

    # Save to file if requested
    if args.output:
        os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else ".", exist_ok=True)
        with open(args.output, "w") as f:
            f.write(output_json)
        print(f"[cli] Output saved to: {args.output}")


if __name__ == "__main__":
    main()