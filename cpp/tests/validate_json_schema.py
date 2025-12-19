#!/usr/bin/env python3
"""Validate JSON output schema from similarity detector."""
import json
import subprocess
import sys
from typing import Any


def _validate_required_keys(data: dict, required_keys: list[str]) -> list[str]:
    """Check that all required top-level keys are present."""
    return [f"Missing required key: {key}" for key in required_keys if key not in data]


def _validate_summary(summary: dict) -> list[str]:
    """Validate the summary section schema and types."""
    errors = []

    required_keys = [
        "analysis_time_ms",
        "clone_pairs_found",
        "estimated_duplication",
        "files_analyzed",
        "total_lines",
    ]
    for key in required_keys:
        if key not in summary:
            errors.append(f"summary missing key: {key}")

    # Type checks for integer fields
    int_fields = [
        "analysis_time_ms",
        "clone_pairs_found",
        "files_analyzed",
        "total_lines",
    ]
    for field in int_fields:
        if field in summary and not isinstance(summary[field], int):
            errors.append(f"summary.{field} should be int")

    # Type check for string field
    if "estimated_duplication" in summary and not isinstance(
        summary["estimated_duplication"], str
    ):
        errors.append("summary.estimated_duplication should be string")

    return errors


def _validate_timing(timing: dict) -> list[str]:
    """Validate the timing section schema and types."""
    errors = []
    timing_keys = ["hash_ms", "match_ms", "tokenize_ms", "total_ms"]

    for key in timing_keys:
        if key not in timing:
            errors.append(f"timing missing key: {key}")
        elif not isinstance(timing[key], int):
            errors.append(f"timing.{key} should be int")

    return errors


def _validate_metrics(metrics: dict) -> list[str]:
    """Validate the metrics section schema."""
    errors = []
    if "by_language" not in metrics:
        errors.append("metrics missing by_language")
    if "by_type" not in metrics:
        errors.append("metrics missing by_type")
    return errors


def _validate_clone_location(loc: dict, clone_idx: int, loc_idx: int) -> list[str]:
    """Validate a single clone location entry."""
    errors = []
    loc_keys = ["end_line", "file", "snippet_preview", "start_line"]

    for key in loc_keys:
        if key not in loc:
            errors.append(
                f"clones[{clone_idx}].locations[{loc_idx}] missing key: {key}"
            )

    return errors


def _validate_clone_entry(clone: dict, idx: int) -> list[str]:
    """Validate a single clone entry."""
    errors = []
    clone_keys = ["id", "locations", "recommendation", "similarity", "type"]

    for key in clone_keys:
        if key not in clone:
            errors.append(f"clones[{idx}] missing key: {key}")

    # Validate locations array
    if "locations" in clone:
        if not isinstance(clone["locations"], list) or len(clone["locations"]) < 2:
            errors.append(f"clones[{idx}].locations should have at least 2 locations")
        else:
            for j, loc in enumerate(clone["locations"]):
                errors.extend(_validate_clone_location(loc, idx, j))

    # Validate similarity field
    if "similarity" in clone:
        if not isinstance(clone["similarity"], (int, float)):
            errors.append(f"clones[{idx}].similarity should be number")
        elif not (0.0 <= clone["similarity"] <= 1.0):
            errors.append(f"clones[{idx}].similarity should be between 0 and 1")

    return errors


def _validate_clones(clones: Any) -> list[str]:
    """Validate the clones array."""
    if not isinstance(clones, list):
        return ["clones should be array"]

    errors = []
    for i, clone in enumerate(clones):
        errors.extend(_validate_clone_entry(clone, i))
    return errors


def _validate_hotspots(hotspots: Any) -> list[str]:
    """Validate the hotspots array."""
    if not isinstance(hotspots, list):
        return ["hotspots should be array"]

    errors = []
    hotspot_keys = ["clone_count", "duplication_score", "file", "recommendation"]

    for i, hotspot in enumerate(hotspots):
        for key in hotspot_keys:
            if key not in hotspot:
                errors.append(f"hotspots[{i}] missing key: {key}")

    return errors


def validate_schema(data: dict) -> list[str]:
    """Validate the JSON output schema and return any errors."""
    errors = []

    # Required top-level keys
    required_keys = ["clones", "hotspots", "metrics", "summary", "timing"]
    errors.extend(_validate_required_keys(data, required_keys))

    # Validate each section
    if "summary" in data:
        errors.extend(_validate_summary(data["summary"]))

    if "timing" in data:
        errors.extend(_validate_timing(data["timing"]))

    if "metrics" in data:
        errors.extend(_validate_metrics(data["metrics"]))

    if "clones" in data:
        errors.extend(_validate_clones(data["clones"]))

    if "hotspots" in data:
        errors.extend(_validate_hotspots(data["hotspots"]))

    return errors


def main():
    # Run the detector and capture output
    result = subprocess.run(
        ["./static_analysis_motor", "--root", "../tests/fixtures", "--ext", ".py"],
        capture_output=True,
        text=True,
        cwd="/home/jesusramos/Workspace/AEGIS/cpp/build",
    )

    if result.returncode != 0:
        print(f"ERROR: Detector failed with code {result.returncode}")
        print(result.stderr)
        sys.exit(1)

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON output: {e}")
        sys.exit(1)

    # Validate schema
    errors = validate_schema(data)

    if errors:
        print("SCHEMA VALIDATION FAILED:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    print("SCHEMA VALIDATION PASSED")
    print(f"  - {len(data['clones'])} clones validated")
    print(f"  - {len(data['hotspots'])} hotspots validated")
    print("  - All required fields present and correctly typed")

    # Additional checks
    print("\nSample clone entry:")
    if data["clones"]:
        print(json.dumps(data["clones"][0], indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
