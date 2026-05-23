"""
analyse_nl.py — Analysis functions for the Dutch North Sea decommissioning pipeline.

Five public functions:
  flag_ownership_transfers(group_a)           — wells where operator ≠ legal owner
  build_production_dataframe(raw_dir, years)  — aggregate monthly production to annual totals
  find_informal_cessation(group_a, annual)    — wells silent for 2+ consecutive years
  build_accountability_table(...)             — final ranked table per legal owner
  build_operator_table(group_a)               — ranked table per operator (clientOrgName)

Key concepts
------------
clientOrgName:  The operating company — who drilled and last ran the well.
legalOwnerName: The current licence holder — who is legally responsible for decommissioning.
                These diverge for 91% of inactive Dutch offshore wells because licences
                have been sold and transferred repeatedly since the 1970s.

EBN (Energie Beheer Nederland) holds a statutory 40% share in all Dutch upstream licences,
meaning roughly 40% of any decommissioning cost falls on the Dutch state by law.
"""

import json
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TODAY                      = pd.Timestamp.now(tz="UTC")
_HC_RESULT_CODES            = {"GAS", "OIL", "OAG", "GOS", "GSS", "OLS", "OWGS", "GWOS"}
_CONSECUTIVE_ZERO_THRESHOLD = 2   # years of zero production = informal cessation
_MONTH_COLS                 = ["jan", "feb", "mar", "apr", "may", "jun",
                                "jul", "aug", "sep", "oct", "nov", "dec"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _years_since(ts: pd.Series) -> pd.Series:
    """Return fractional years between a datetime Series and today. Nulls propagate."""
    return ((_TODAY - ts).dt.days / 365.25)


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def flag_ownership_transfers(group_a: pd.DataFrame) -> pd.DataFrame:
    """Return Group A wells where the operator differs from the legal owner.

    When a licence is sold, the new owner becomes legally responsible for
    decommissioning but the original operator's name remains in the borehole
    record as clientOrgName. These mismatches identify transferred liabilities.

    Args:
        group_a: Group A DataFrame from clean_nl.split_groups.

    Returns:
        DataFrame of transfer wells with boreholeName, clientOrgName,
        legalOwnerName, statusDescription, resultCode, endDate.
    """
    mask = (
        group_a["clientOrgName"].notna()
        & group_a["legalOwnerName"].notna()
        & (group_a["clientOrgName"] != group_a["legalOwnerName"])
    )
    cols = ["boreholeName", "clientOrgName", "legalOwnerName",
            "statusDescription", "resultCode", "endDate"]
    return group_a[mask][cols].copy().reset_index(drop=True)


def build_production_dataframe(raw_dir: Path, years: list[int]) -> pd.DataFrame:
    """Load saved production JSON files and return a tidy annual-total DataFrame.

    Expects files named `production_Gas_{year}.json` and `production_Oil_{year}.json`
    in raw_dir, as saved by fetch_nl.fetch_production.

    Monthly figures (jan–dec) are summed to an annual total per well per product.

    Args:
        raw_dir: Directory containing the raw production JSON files.
        years:   List of integer years to load.

    Returns:
        DataFrame with columns: boreholeName, year, product, annual_total.
    """
    frames = []
    for product in ("Gas", "Oil"):
        for year in years:
            fpath = raw_dir / f"production_{product}_{year}.json"
            if not fpath.exists():
                logger.warning("Missing production file: %s", fpath)
                continue
            data = json.loads(fpath.read_text())
            if not data:
                continue
            df_yr = pd.DataFrame(data)
            present_months = [m for m in _MONTH_COLS if m in df_yr.columns]
            df_yr["annual_total"] = df_yr[present_months].sum(axis=1)
            df_yr = df_yr.rename(columns={"wellNm": "boreholeName"})
            df_yr["year"]    = year
            df_yr["product"] = product
            frames.append(df_yr[["boreholeName", "year", "product", "annual_total"]])

    if not frames:
        logger.warning("No production data loaded.")
        return pd.DataFrame(columns=["boreholeName", "year", "product", "annual_total"])

    annual = (
        pd.concat(frames, ignore_index=True)
        .groupby(["boreholeName", "year", "product"], as_index=False)["annual_total"]
        .sum()
    )
    logger.info("Production summary: %d well-year-product rows, %d unique wells",
                len(annual), annual["boreholeName"].nunique())
    return annual


def find_informal_cessation(group_a: pd.DataFrame,
                             annual: pd.DataFrame) -> pd.DataFrame:
    """Identify Group A wells confirmed inactive by production data.

    A well is an informal cessation candidate if it appears in the production
    dataset with zero output for two or more consecutive years. Wells absent
    from the production data entirely are also counted as zero.

    This catches wells where the formal borehole record shows cessation years
    ago but production figures confirm the well has been completely silent —
    important because the formal record may lag reality or be missing entirely.

    Args:
        group_a: Group A DataFrame from clean_nl.split_groups.
        annual:  Annual production summary from build_production_dataframe.

    Returns:
        DataFrame of informal cessation candidates with consecutive_zero_years
        and zero_from_year columns joined to Group A attributes.
    """
    years_sorted = sorted(annual["year"].unique())

    pivot = (
        annual.groupby(["boreholeName", "year"])["annual_total"]
        .sum()
        .unstack(fill_value=0)
        .reindex(columns=years_sorted, fill_value=0)
    )

    results = []
    for well, row in pivot.iterrows():
        consecutive = max_consecutive = 0
        zero_from = None
        for yr in years_sorted:
            if row[yr] == 0:
                if consecutive == 0:
                    zero_from = yr
                consecutive += 1
                max_consecutive = max(max_consecutive, consecutive)
            else:
                consecutive = 0
        if max_consecutive >= _CONSECUTIVE_ZERO_THRESHOLD:
            results.append({
                "boreholeName":          well,
                "consecutive_zero_years": max_consecutive,
                "zero_from_year":         zero_from,
            })

    zero_df = pd.DataFrame(results)
    if zero_df.empty:
        return pd.DataFrame()

    ga_cols = ["boreholeName", "clientOrgName", "legalOwnerName",
               "statusDescription", "resultCode", "endDate", "blockCd"]
    merged = (
        group_a[ga_cols]
        .merge(zero_df, on="boreholeName", how="inner")
        .sort_values(["consecutive_zero_years", "boreholeName"], ascending=[False, True])
        .reset_index(drop=True)
    )
    logger.info("Informal cessation candidates: %d wells", len(merged))
    return merged


def build_accountability_table(group_a: pd.DataFrame,
                                informal: pd.DataFrame,
                                ghost: pd.DataFrame) -> pd.DataFrame:
    """Build the final accountability table ranked by legal owner.

    The legal owner (legalOwnerName) is the entity that holds the current
    decommissioning liability, not necessarily the company that drilled the well.
    Because EBN co-owns all Dutch licences, roughly 40% of every cost in this
    table ultimately falls on the Dutch state.

    Args:
        group_a:  Group A DataFrame (320 inactive offshore wells).
        informal: Informal cessation candidates from find_informal_cessation.
        ghost:    Ghost wells DataFrame from clean_nl.split_groups.

    Returns:
        DataFrame ranked by inactive_well_count, one row per legal owner.
    """
    working = group_a.copy()
    working["legalOwnerName"] = working["legalOwnerName"].fillna("[Unknown]")
    working["confirmed_inactive"] = working["boreholeName"].isin(
        set(informal["boreholeName"]) if not informal.empty else set()
    ).astype(int)
    working["is_transfer"] = (
        working["clientOrgName"].notna()
        & working["legalOwnerName"].notna()
        & (working["clientOrgName"] != working["legalOwnerName"])
    ).astype(int)
    working["years_inactive"] = _years_since(working["endDate"])

    ghost_counts = (
        ghost.copy()
        .assign(legalOwnerName=lambda d: d["legalOwnerName"].fillna("[Unknown]"))
        .groupby("legalOwnerName")
        .size()
        .rename("ghost_wells")
    )

    table = (
        working.groupby("legalOwnerName", dropna=False)
        .agg(
            inactive_well_count  = ("boreholeDbk",       "count"),
            mean_years_inactive  = ("years_inactive",     "mean"),
            max_years_inactive   = ("years_inactive",     "max"),
            confirmed_inactive   = ("confirmed_inactive", "sum"),
            transferred_wells    = ("is_transfer",        "sum"),
            result_codes         = ("resultCode",
                                    lambda s: ", ".join(sorted(s.dropna().unique()))),
            earliest_spud        = ("startDate",          "min"),
        )
        .reset_index()
        .join(ghost_counts, on="legalOwnerName", how="left")
    )
    table["ghost_wells"]         = table["ghost_wells"].fillna(0).astype(int)
    table["mean_years_inactive"] = table["mean_years_inactive"].round(1)
    table["max_years_inactive"]  = table["max_years_inactive"].round(1)
    table["earliest_spud"]       = table["earliest_spud"].dt.year

    return table.sort_values("inactive_well_count", ascending=False).reset_index(drop=True)


def build_operator_table(group_a: pd.DataFrame) -> pd.DataFrame:
    """Build a reference table ranked by operator (clientOrgName).

    Complementary to build_accountability_table. Because operator names in the
    NLOG dataset are not normalised (e.g. 'Placid', 'Placid International Oil, Ltd.',
    'Placid International Oil Ltd.' are all the same company), totals here will
    undercount consolidated entities. Use legalOwnerName for the primary story.

    Args:
        group_a: Group A DataFrame from clean_nl.split_groups.

    Returns:
        DataFrame ranked by well_count, one row per clientOrgName variant.
    """
    working = group_a.copy()
    working["clientOrgName"] = working["clientOrgName"].fillna("[Unknown operator]")
    working["is_transfer"]   = (
        working["clientOrgName"].notna()
        & working["legalOwnerName"].notna()
        & (working["clientOrgName"] != working["legalOwnerName"])
    ).astype(int)
    working["years_inactive"] = _years_since(working["endDate"])

    table = (
        working.groupby("clientOrgName", dropna=False)
        .agg(
            well_count          = ("boreholeDbk", "count"),
            result_codes        = ("resultCode",
                                   lambda s: ", ".join(sorted(s.dropna().unique()))),
            earliest_spud       = ("startDate",   "min"),
            latest_cessation    = ("endDate",      "max"),
            mean_years_inactive = ("years_inactive", "mean"),
            ownership_transfers = ("is_transfer",  "sum"),
        )
        .reset_index()
        .sort_values("well_count", ascending=False)
        .reset_index(drop=True)
    )
    table["mean_years_inactive"] = table["mean_years_inactive"].round(1)
    table["earliest_spud"]       = table["earliest_spud"].dt.year
    table["latest_cessation"]    = table["latest_cessation"].dt.year
    return table
