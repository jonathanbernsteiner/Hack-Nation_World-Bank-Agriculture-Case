"""Local processing: `python -m hotline.cli process <conversation_id>` or `process --pending`.
Exit code is non-zero when a call fails or cannot be found."""

import argparse
import sys

from hotline.pipeline import process

OK_STATUSES = frozenset({"processed", "needs_review"})


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hotline.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    proc = sub.add_parser("process", help="process one call, or all pending calls")
    proc.add_argument("conversation_id", nargs="?")
    proc.add_argument("--pending", action="store_true", help="process pending calls (up to --limit)")
    proc.add_argument("--limit", type=int, default=process.DEFAULT_PENDING_LIMIT)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if bool(args.conversation_id) == bool(args.pending):
        parser.error("give a conversation_id or --pending, not both")
    statuses = (
        process.process_pending(args.limit) if args.pending else [process.process_call(args.conversation_id)]
    )
    for status in statuses:
        print(status)
    return 0 if all(status in OK_STATUSES for status in statuses) else 1


if __name__ == "__main__":
    sys.exit(main())
