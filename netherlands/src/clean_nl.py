"""
clean_nl.py — Loading and filtering for the Dutch North Sea decommissioning pipeline.

Three public functions:
  load_boreholes(path)    — load raw JSON into a pandas DataFrame, convert dates
  filter_offshore(df)     — keep only offshore wells (onOffshore == 'OFF')
  split_groups(offshore)  — split offshore wells into Group A, Group B, ghost wells

Group definitions
-----------------
Group A — inactive offshore wells (core accountability table):
    statusDescription in {'Suspended', 'Closed-In'}
    All result codes included — non-hydrocarbon wells carry the same decommissioning
    obligation as hydrocarbon wells. resultCode is retained as a column.

Group B — sidetracked offshore wells:
    statusDescription == 'Sidetracked'
    Incomplete / abandoned mid-drill; secondary story.

Ghost wells — offshore wells with no status on record:
    statusDescription is null
    All are recent (2021 onwards); likely freshly drilled wells pending classification.

Excluded entirely:
    statusDescription in {'Plugged and abandoned', 'Producing/Injecting', 'Monitoring'}
"""

import json
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Group definitions
# ---------------------------------------------------------------------------

_INACTIVE_STATUSES = {"Suspended", "Closed-In"}
_EXCLUDE_STATUSES  = {"Plugged and abandoned", "Producing/Injecting", "Monitoring"}

# Date columns stored as Unix milliseconds in the raw API response
_DATE_COLS = ("startDate", "endDate", "confidentialityDate")


def load_boreholes(path: Path) -> pd.DataFrame:
    """Load raw borehole JSON into a DataFrame and convert date columns.

    Date fields in the NLOG API are Unix milliseconds (integer). This function
    converts them to timezone-aware pandas datetimes (UTC).

    Args:
        path: Path to the raw JSON file produced by fetch_nl.fetch_boreholes.

    Returns:
        DataFrame with 21 columns and one row per well.
    """
    data = json.loads(path.read_text())
    df = pd.DataFrame(data)
    for col in _DATE_COLS:
        df[col] = pd.to_datetime(df[col], unit="ms", utc=True, errors="coerce")
    logger.info("Loaded boreholes: %d rows × %d cols", *df.shape)
    return df


def filter_offshore(df: pd.DataFrame) -> pd.DataFrame:
    """Return only offshore wells (onOffshore == 'OFF').

    The NLOG dataset covers both onshore and offshore wells. The investigation
    focuses entirely on offshore wells in the Dutch North Sea continental shelf.

    Args:
        df: Full boreholes DataFrame from load_boreholes.

    Returns:
        Filtered DataFrame containing only offshore records.
    """
    offshore = df[df["onOffshore"] == "OFF"].copy()
    logger.info("Offshore wells: %d (of %d total)", len(offshore), len(df))
    return offshore


def split_groups(offshore: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split offshore wells into Group A (inactive), Group B (sidetracked), ghost.

    Args:
        offshore: Offshore-only DataFrame from filter_offshore.

    Returns:
        Tuple of (group_a, group_b, ghost) DataFrames.
    """
    group_a = offshore[offshore["statusDescription"].isin(_INACTIVE_STATUSES)].copy()
    group_b = offshore[offshore["statusDescription"] == "Sidetracked"].copy()
    ghost   = offshore[offshore["statusDescription"].isna()].copy()

    logger.info("Group A (inactive): %d", len(group_a))
    logger.info("Group B (sidetracked): %d", len(group_b))
    logger.info("Ghost (null status): %d", len(ghost))
    return group_a, group_b, ghost
