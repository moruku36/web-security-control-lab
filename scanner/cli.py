"""Command Line Interface for Web Security Control Lab Scanner.

Exit codes: 0 completed report (observed weaknesses included), 1 no subcommand,
2 target refusal or argument error, 3 incomplete inspection or runtime error.
"""

import argparse
import sys
from urllib.parse import urlparse

from scanner.checks import run_inspection
from scanner.models import MODES, ReasonCode, build_error_report
from scanner.reporter import format_json_report, format_text_report
from scanner.target import validate_target_url

URL_FORM_MESSAGE = (
    "Refusing target. Use a bare base URL of the form scheme://host[:port] "
    "without credentials, path, query or fragment."
)


def normalize_base_url(validated_url: str) -> str:
    """Return scheme://host[:port], or raise ValueError for any other URL form.

    Nothing from a refused URL is echoed back.
    """
    if "?" in validated_url or "#" in validated_url or "@" in validated_url:
        raise ValueError(URL_FORM_MESSAGE)
    parsed = urlparse(validated_url)
    try:
        parsed.port
    except ValueError:
        raise ValueError(URL_FORM_MESSAGE) from None
    if parsed.path not in ("", "/") or parsed.params or not parsed.netloc:
        raise ValueError(URL_FORM_MESSAGE)
    return f"{parsed.scheme}://{parsed.netloc}"


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
    scan_parser.add_argument(
        "--expected-mode",
        choices=list(MODES),
        default=None,
        help="Mode the target is expected to report; a mismatch makes every check ERROR.",
    )

    return parser


def main(args=None, transport=None, clock=None) -> int:
    parser = build_parser()
    parsed_args = parser.parse_args(args)

    if not parsed_args.command:
        parser.print_help()
        return 1

    if parsed_args.command == "scan":
        # Validate target under Fail-Closed policy before any request
        try:
            validated_url = validate_target_url(parsed_args.target)
            base_url = normalize_base_url(validated_url)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2

        try:
            report = run_inspection(
                base_url,
                expected_mode=parsed_args.expected_mode,
                transport=transport,
                clock=clock,
            )
        except Exception:
            # Fixed message only: exception text is never printed.
            report = build_error_report(base_url, ReasonCode.UNEXPECTED_RESPONSE, clock=clock)

        if parsed_args.format == "json":
            print(format_json_report(report))
        else:
            print(format_text_report(report))

        if report.has_errors:
            print("Inspection incomplete: at least one check reported ERROR.", file=sys.stderr)
            return 3
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
