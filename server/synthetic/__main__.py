"""CLI: python -m synthetic [--dry-run] [--reset] [--skip-salt-check].

Reads LEDGER_PIN_SALT, HOTLINE_ADMIN_SECRET and DATABASE_URL from the environment (source
.env first). Prints counts only, never a secret.
"""

import argparse
import os
import sys

from . import supabase as loader
from .generate import generate_season


def _parse(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m synthetic", description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print row counts, touch nothing")
    parser.add_argument("--reset", action="store_true", help="delete only is_synthetic rows first")
    parser.add_argument("--skip-salt-check", action="store_true",
                        help="local databases only; refused for the production Supabase host")
    return parser.parse_args(argv)


def _connect(url: str):
    import psycopg  # lazy: only the live load needs it (run with the hotline environment)

    return psycopg.connect(url, prepare_threshold=None, connect_timeout=10, autocommit=False)


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)
    season = generate_season()
    if args.dry_run:
        print(loader.format_counts("would insert", loader.season_counts(season)))
        print(loader.format_counts("entry currencies", loader.entry_currencies(season)))
        return 0
    salt = os.environ.get("LEDGER_PIN_SALT")
    database_url = os.environ.get("DATABASE_URL")
    try:
        if not database_url:
            raise loader.LoadError("DATABASE_URL is not set")
        if args.skip_salt_check:
            loader.refuse_skip_for_production(database_url)
            if not salt:
                raise loader.SaltGateError("LEDGER_PIN_SALT is not set")
        else:
            loader.check_salt_gate(salt, os.environ.get("HOTLINE_ADMIN_SECRET"))
        conn = _connect(database_url)
        try:
            result = loader.run_load(conn, salt, args.reset, season)
        finally:
            conn.close()
    except loader.LoadError as error:
        print(f"refused: {error}", file=sys.stderr)
        return 1
    if result["deleted"]:
        print(loader.format_counts("deleted", result["deleted"]))
    print(loader.format_counts("inserted", result["inserted"]))
    median, sales, farmers = result["median"]
    print(f"Kyabakuza kiboko median={median} from {sales} sales by {farmers} farmers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
