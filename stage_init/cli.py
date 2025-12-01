"""
Command-line entry point for stage-aware project initialization.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Iterable, Optional

import assess_stage

from .initializer import InitializationConfig, ProjectInitializer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Stage-Aware Development Framework - Initialize projects with automatic stage detection",
    )
    parser.add_argument(
        "project_path",
        help="Project name (new project) or path (existing project with --existing)",
    )
    parser.add_argument(
        "--existing",
        action="store_true",
        help="Treat project_path as an existing directory",
    )
    parser.add_argument(
        "--detect-only",
        action="store_true",
        help="Only detect and display stage, don't initialize framework",
    )
    parser.add_argument(
        "--agent",
        choices=["claude", "codex", "gemini", "both", "all"],
        default="both",
        help="Which agent integrations to prepare (default: both). 'all' includes Claude, Codex and Gemini.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate actions without modifying the filesystem",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files (clean install)",
    )
    parser.add_argument(
        "--skip-claude-init",
        action="store_true",
        help="Do not invoke `claude -p /init` even if the CLI is available",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        help="Logging level to use during initialization",
    )
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(levelname)s %(message)s",
    )
    log = logging.getLogger("stage_init")

    project_path = Path(args.project_path)

    if args.detect_only:
        assessment = assess_stage.assess_stage(project_path)
        assess_stage.print_assessment(assessment)
        return 0

    if args.existing and not project_path.exists():
        parser.error(f"Project directory not found: {project_path}")

    config = InitializationConfig(
        project_path=project_path,
        existing_project=args.existing,
        agent_selection=args.agent,
        dry_run=args.dry_run,
        run_claude_init=not args.skip_claude_init,
        force=args.force,
    )

    initializer = ProjectInitializer(config, logger_override=log)
    result = initializer.run()

    _print_summary(result, config, log)
    return 0


def _print_summary(result, config: InitializationConfig, log: logging.Logger) -> None:
    dest_dir = result.dest_dir
    project_name = dest_dir.name

    prefix = "[dry-run] " if config.dry_run else ""
    print(f"{prefix}✓ Project '{project_name}' initialized at {dest_dir}")

    claude_dir = dest_dir / ".claude"
    codex_dir = dest_dir / ".codex"
    docs_dir = dest_dir / "docs"

    if config.agent_selection in {"claude", "both", "all"}:
        print(f"✓ Claude context files at: {claude_dir}")
    else:
        print(
            f"ℹ️ Claude integration skipped (--agent={config.agent_selection}); core stage files stored at: {claude_dir}"
        )

    if config.agent_selection in {"gemini", "both", "all"}:
        gemini_dir = dest_dir / ".gemini"
        print(f"✓ Gemini context files at: {gemini_dir}")
    else:
        print(f"ℹ️ Gemini integration skipped (--agent={config.agent_selection})")

    if config.agent_selection in {"codex", "both", "all"}:
        print(f"✓ Codex instructions at: {codex_dir}")
    else:
        print(f"ℹ️ Codex integration skipped (--agent={config.agent_selection})")

    print(f"✓ Reference docs at: {docs_dir}")

    for category, summary in result.template_summaries.items():
        if summary.copied:
            print(f"\nAdded {len(summary.copied)} {category} file(s):")
            for item in summary.copied:
                _print_file_change(item, "+", dest_dir)
        if summary.updated:
            print(f"\nUpdated {len(summary.updated)} {category} file(s):")
            for item in summary.updated:
                _print_file_change(item, "~", dest_dir)
        if summary.skipped:
            print(f"\nSkipped {len(summary.skipped)} existing {category} file(s):")
            for item in summary.skipped:
                _print_file_change(item, "-", dest_dir)

    stage_result = result.stage_update
    if stage_result and stage_result.assessment:
        stage = stage_result.assessment.recommended_stage
        confidence = stage_result.assessment.confidence
        print(f"\nStage detection: Stage {stage} ({confidence} confidence)")
        for reason in stage_result.assessment.reasons[:5]:
            print(f"  • {reason}")
        if not config.dry_run and stage_result.current_phase_updated:
            print("Updated .claude/01-current-phase.md with detected stage.")
    else:
        print("\nStage detection unavailable.")

    print("\nNext steps:")
    print(f"  cd {dest_dir}")
    print("  cat docs/QUICK_START.md  # Read this first")
    if config.dry_run:
        print("  # Re-run without --dry-run to apply these changes")
    else:
        if config.agent_selection == "all":
            print("  # Agents ready: Claude Code + Codex CLI + Gemini CLI")
        elif config.agent_selection == "both":
            print("  # Agents ready: Claude Code + Codex CLI")
        elif config.agent_selection == "claude":
            print("  # Agent ready: Claude Code")
        elif config.agent_selection == "gemini":
            print("  # Agent ready: Gemini CLI")
        else:
            print("  # Agent ready: Codex CLI")


def _print_file_change(path: Path, marker: str, dest_dir: Path) -> None:
    try:
        relative = path.relative_to(dest_dir)
    except ValueError:
        relative = path
    print(f"  {marker} {relative}")


if __name__ == "__main__":
    import sys

    sys.exit(main())
