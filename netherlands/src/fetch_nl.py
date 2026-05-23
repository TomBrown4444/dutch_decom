"""
fetch_nl.py — NLOG data fetcher for the Dutch North Sea decommissioning pipeline.

Two public functions:
  fetch_boreholes(session, path)          — all 6,723 wells from the borehole API
  fetch_production(session, year, product, path) — monthly production per well

Both require a requests.Session seeded against the NLOG datacenter (see seed_session).
The session cookie (JSESSIONID) is set automatically by the seed GET; no credentials needed.

API notes:
  Boreholes endpoint returns all records in a single JSON array — no pagination.
  Production endpoint takes yearStart/yearEnd/product/production in the POST body.
  Data available from 2003; updated daily.
"""

import json
import logging
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

_SEED_URL      = "https://www.nlog.nl/datacenter/brh-overview"
_BOREHOLES_URL = "https://www.nlog.nl/nlog-mapviewer/rest/brh/boreholes"
_PROD_URL      = "https://www.nlog.nl/nlog-mapviewer/rest/prodfigures/well"
_TIMEOUT       = 60  # seconds


def seed_session() -> requests.Session:
    """Open an HTTPS session and hit the NLOG datacenter to set the required cookie.

    The NLOG APIs require a valid JSESSIONID cookie, which is issued on the
    first GET to any datacenter page. No login or API key is needed.

    Returns:
        A requests.Session with the JSESSIONID cookie already set.
    """
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; research/1.0)"})
    resp = session.get(_SEED_URL, timeout=_TIMEOUT)
    resp.raise_for_status()
    logger.info("Session seeded — cookies: %s", list(session.cookies.keys()))
    return session


def fetch_boreholes(session: requests.Session, path: Path) -> list:
    """POST to the NLOG boreholes endpoint and save raw JSON to disk.

    Returns all wells in a single response (~6,700 records). No pagination needed.
    Saves the raw array to `path` so downstream steps can reload without re-fetching.

    Args:
        session: A seeded requests.Session (from seed_session).
        path:    File path for the raw JSON output.

    Returns:
        The parsed list of borehole records.
    """
    resp = session.post(_BOREHOLES_URL, timeout=_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    logger.info("Boreholes: %d records", len(data))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    logger.info("Saved boreholes → %s", path)
    return data


def fetch_production(session: requests.Session,
                     year: int,
                     product: str,
                     path: Path) -> list:
    """POST to the NLOG production endpoint for one year and product type.

    Returns monthly production figures for every reporting well.
    Data is available from 2003 onwards; pre-2003 figures are not in the public domain.

    Args:
        session: A seeded requests.Session (from seed_session).
        year:    The calendar year to fetch (e.g. 2023).
        product: "Gas" or "Oil".
        path:    File path for the raw JSON output.

    Returns:
        The parsed list of production records.
    """
    payload = {
        "yearStart":  year,
        "yearEnd":    year,
        "product":    product,
        "production": "Produced",
    }
    resp = session.post(_PROD_URL, json=payload, timeout=_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    logger.info("Production %s %d: %d records", product, year, len(data))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    logger.info("Saved production → %s", path)
    return data
