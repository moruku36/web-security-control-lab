"""Command Line Interface for Web Security Control Lab Scanner."""

import argparse
import sys

from scanner.checks import run_all_checks
from scanner.models import ScanReport
from scanner.reporter import compute_summary, format_json_report, format_text_report
from scanner.target import validate_target_url


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="security-lab",
        description="Web Security Control Lab Scanner: Safe local educational scanner.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    scan_parser = subparsers.add_parser("scan", help="Scan local lab application")
    scan_parser.add_argument(
        "target",
        help="Target base URL (e.g. http://127.0.0.1:8000). Only localhost targets are permitted.",
    )
    scan_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output presentation format (default: text)",
    )

    return parser


def main(args=None) -> int:
    parser = build_parser()
    parsed_args = parser.parse_args(args)

    if not parsed_args.command:
        parser.print_help()
        return 1

    if parsed_args.command == "scan":
        target = parsed_args.target
        # Validate target under Fail-Closed policy
        try:
            validated_url = validate_target_url(target)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2

        try:
            findings = run_all_checks(validated_url)
        except Exception as e:
            print(f"Scan failed: {e}", file=sys.stderr)
            return 3

        summary = compute_summary(findings)
        report = ScanReport(target=validated_url, findings=findings, summary=summary)

        if parsed_args.format == "json":
            print(format_json_report(report))
        else:
            print(format_text_report(report))

        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
