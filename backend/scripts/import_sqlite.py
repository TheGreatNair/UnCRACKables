"""Import existing SQLite reports into the DATABASE_URL configured target."""

import argparse
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import BACKEND_ROOT, settings  # noqa: E402
from app.database import build_engine  # noqa: E402
from app.importer import import_sqlite_reports  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=BACKEND_ROOT / "turtleway.db",
        help="Existing SQLite file (read only; defaults to backend/turtleway.db)",
    )
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    engine = build_engine(settings.sqlalchemy_database_url)
    summary = import_sqlite_reports(args.source, engine)
    print(
        f"Verified {summary.verified_count} IDs from {summary.source_count} source rows; "
        f"inserted {summary.inserted_count}, already present {summary.already_present_count}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
