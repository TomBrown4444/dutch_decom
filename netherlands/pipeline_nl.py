"""
pipeline_nl.py — Dutch North Sea decommissioning pipeline.

Orchestrates:
  1. Fetch    — pull all boreholes and production figures from the NLOG API
  2. Clean    — filter offshore wells, split into Group A / B / ghost
  3. Analyse  — operator table, ownership transfers, production crossref,
                accountability table
  4. Save     — write all outputs to netherlands/data/ and netherlands/outputs/

The investigation question: which operators are sitting on inactive Dutch offshore
wells with no decommissioning programme, and how long have those wells been idle?

This builds the table that does not yet publicly exist in the Netherlands —
equivalent to what the UK's NSTA publishes for the British continental shelf.

Usage:
  python netherlands/pipeline_nl.py              # full run
  python netherlands/pipeline_nl.py --skip-fetch # reuse existing raw data

Environment variables (optional — only needed if extending to email notification):
  Load from a .env file in the project root via python-dotenv.
"""

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

# load_dotenv() is called exactly once, here at module level
load_dotenv(Path(__file__).parent.parent / ".env")

from src.fetch_nl   import seed_session, fetch_boreholes, fetch_production
from src.clean_nl   import load_boreholes, filter_offshore, split_groups
from src.analyse_nl import (
    flag_ownership_transfers,
    build_production_dataframe,
    find_informal_cessation,
    build_accountability_table,
    build_operator_table,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths — all relative to this file's location (netherlands/)
# ---------------------------------------------------------------------------

_HERE          = Path(__file__).parent
_DATA_RAW      = _HERE / "data" / "raw"
_DATA_PROC     = _HERE / "data" / "processed"
_DATA_STATE    = _HERE / "data" / "state"
_OUTPUTS       = _HERE / "outputs"

_BOREHOLES_RAW = _DATA_RAW  / "nlog_boreholes_raw.json"
_OPERATOR_CSV  = _DATA_PROC / "group_a_by_operator.csv"
_INFORMAL_CSV  = _DATA_PROC / "informal_cessation_wells.csv"
_TRANSFERS_CSV = _DATA_PROC / "ownership_transfers.csv"
_ACCOUNT_CSV   = _OUTPUTS   / "nl_wells_analysis.csv"
_OP_VIEW_CSV   = _OUTPUTS   / "nl_wells_by_operator.csv"

_PROD_YEARS    = list(range(2020, 2026))   # 2020–2025 inclusive


def _make_dirs() -> None:
    """Create all required output directories if they do not exist."""
    for d in (_DATA_RAW, _DATA_PROC, _DATA_STATE, _OUTPUTS):
        d.mkdir(parents=True, exist_ok=True)


def _fetch_all(skip: bool) -> None:
    """Fetch borehole and production data from NLOG. Skip if --skip-fetch passed."""
    if skip:
        logger.info("--skip-fetch: reusing existing raw data")
        return

    session = seed_session()
    fetch_boreholes(session, _BOREHOLES_RAW)

    for product in ("Gas", "Oil"):
        for year in _PROD_YEARS:
            path = _DATA_RAW / f"production_{product}_{year}.json"
            fetch_production(session, year, product, path)


def _run_pipeline() -> None:
    """Execute the full clean → analyse → save pipeline."""

    # Clean
    df       = load_boreholes(_BOREHOLES_RAW)
    offshore = filter_offshore(df)
    group_a, group_b, ghost = split_groups(offshore)

    # Analyse
    transfers    = flag_ownership_transfers(group_a)
    annual       = build_production_dataframe(_DATA_RAW, _PROD_YEARS)
    informal     = find_informal_cessation(group_a, annual)
    account_tbl  = build_accountability_table(group_a, informal, ghost)
    operator_tbl = build_operator_table(group_a)

    # Save
    operator_tbl.to_csv(_OPERATOR_CSV,  index=False)
    logger.info("Saved operator table      → %s", _OPERATOR_CSV)

    transfers.to_csv(_TRANSFERS_CSV, index=False)
    logger.info("Saved ownership transfers → %s", _TRANSFERS_CSV)

    if not informal.empty:
        informal.to_csv(_INFORMAL_CSV, index=False)
        logger.info("Saved informal cessation  → %s", _INFORMAL_CSV)

    account_tbl.to_csv(_ACCOUNT_CSV, index=False)
    logger.info("Saved accountability table → %s", _ACCOUNT_CSV)

    operator_tbl.to_csv(_OP_VIEW_CSV, index=False)
    logger.info("Saved operator view        → %s", _OP_VIEW_CSV)

    # Summary
    logger.info("--- Pipeline complete ---")
    logger.info("Offshore wells : %d", len(offshore))
    logger.info("Group A        : %d inactive", len(group_a))
    logger.info("Group B        : %d sidetracked", len(group_b))
    logger.info("Ghost wells    : %d (null status)", len(ghost))
    logger.info("Transfers      : %d wells (%.0f%%)",
                len(transfers), len(transfers) / len(group_a) * 100)
    logger.info("Informal cess. : %d confirmed-inactive wells", len(informal))


def main() -> None:
    """Parse arguments and run the pipeline."""
    parser = argparse.ArgumentParser(description="Dutch North Sea decommissioning pipeline")
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Skip API fetch and reuse existing raw data files",
    )
    args = parser.parse_args()

    _make_dirs()
    _fetch_all(skip=args.skip_fetch)
    _run_pipeline()


if __name__ == "__main__":
    main()
