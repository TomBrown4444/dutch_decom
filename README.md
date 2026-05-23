# Dutch North Sea Decommissioning — Investigative Data Pipeline

> **Status: Preliminary.** Requires operator verification, KvK company checks, and SodM cross-referencing before publication.

This repository contains a data pipeline built to investigate operator compliance with decommissioning obligations on the Dutch Continental Shelf (NCS). It combines live well data from the Netherlands Oil and Gas portal (NLOG) with monthly production figures from the same source to identify inactive offshore wells with no decommissioning programme, and to trace who is currently legally responsible for them.

The pipeline was developed as part of an ongoing investigative journalism project. It is not affiliated with or endorsed by NLOG, TNO, SodM, or any operator named in the outputs.

---

## The Investigation

Unlike the UK, the Netherlands has never published a named operator non-compliance table for well decommissioning. There is no Dutch equivalent of the NSTA's December 2025 disclosure. The accountability picture must be reconstructed from raw well data and production records — which is what this pipeline does.

A structural feature of Dutch energy law makes this investigation particularly significant. EBN (Energie Beheer Nederland) is a state-owned company that holds a statutory 40% participation share in virtually all Dutch oil and gas production licences. The Dutch taxpayer is therefore automatically co-liable for a substantial share of decommissioning costs, regardless of what the operator does or whether the operator has the financial capacity to pay.

This project goes further than describing the current situation in three ways.

**First**, it identifies every inactive offshore well on the Dutch Continental Shelf and attributes it to a current legal owner — building the operator accountability table that SodM has never published.

**Second**, it distinguishes between the company that originally drilled a well and the company now legally responsible for decommissioning it. The NLOG data contains two separate operator fields — `clientOrgName` and `legalOwnerName` — which diverge where a licence has been transferred since drilling. The scale of these transfers, and whether the receiving companies are financially capable of meeting the liability, is a central question of the investigation.

**Third**, it cross-references well status against monthly production figures to identify wells that are confirmed inactive by two independent sources — including wells where the formal status record carries no cessation date but production data shows the well has been silent for years.

---

## Data Sources

### Dataset 1 — NLOG Borehole Administrative Data (API)

| | |
|---|---|
| **Source** | TNO — Geological Survey of the Netherlands, on behalf of the Dutch Ministry of Economic Affairs |
| **Portal** | `https://www.nlog.nl` |
| **Endpoint** | `https://www.nlog.nl/nlog-mapviewer/rest/brh/boreholes` |
| **Method** | POST request with empty body — session cookie required |
| **Session** | Must first GET `https://www.nlog.nl/datacenter/brh-overview` to initialise session cookie. Handled automatically by `requests.Session()`. |
| **Authentication** | None beyond session cookie — fully open |
| **Returns** | 6,723 wells in a single JSON array — no pagination required |
| **Updated** | Daily |

Key fields used:

| Field | Description |
|---|---|
| `boreholeDbk` | Unique numeric well ID |
| `boreholeName` | Full well name |
| `shortName` | Abbreviated well name |
| `clientOrgName` | Operating company at time of drilling |
| `legalOwnerName` | Current legal owner — may differ from `clientOrgName` where licence has been transferred |
| `statusDescription` | Current operational status |
| `resultCode` | Drilling result code — what the well found |
| `onOffshore` | `ON` = onshore / `OFF` = offshore |
| `startDate` | Spud date — Unix milliseconds |
| `endDate` | Cessation date — Unix milliseconds. Absent for some inactive wells. |
| `confidentialityDate` | Date well data entered the public domain — Unix milliseconds |
| `blockCd` | Licence block identifier |

### Dataset 2 — NLOG Production Figures Per Well (API)

| | |
|---|---|
| **Source** | NLOG / TNO, on behalf of the Dutch Ministry of Economic Affairs |
| **Endpoint** | `https://www.nlog.nl/nlog-mapviewer/rest/prodfigures/well` |
| **Method** | POST — payload parameters required. See `netherlands/src/fetch_nl.py` for payload structure. |
| **Format** | Monthly production volumes per well per year |
| **Available from** | January 2003 only — pre-2003 data is not in the public domain |
| **Updated** | Monthly, within approximately eight weeks of each reporting month |

Under Article 111 of the Dutch Mining Decree (Mijnbouwbesluit), operators are legally required to report monthly production figures to TNO. These are published publicly within approximately eight weeks. A well showing zero production across consecutive months has ceased operating regardless of what its formal status record says. This dataset is used to cross-corroborate inactive status and to identify wells where no formal cessation date is recorded but production data confirms inactivity.

---

## Data Notes — Read Before Using Outputs

**Two operator fields exist and frequently diverge.**
`clientOrgName` records the operator at the time of drilling. `legalOwnerName` records the current legal owner. Where these differ, the licence — and with it the legal decommissioning obligation — has been transferred to a new entity since the well was drilled. Both fields must be captured and compared. The scale of divergence across the dataset is a primary analytical finding.

**Dates are Unix milliseconds.**
`startDate`, `endDate`, and `confidentialityDate` are stored as 13-digit integers. Convert with `pd.to_datetime(df['startDate'], unit='ms')`.

**`endDate` is absent for some inactive wells.**
Not all inactive wells carry a formal cessation date in the status record. These are identified and cross-checked against production data. Wells confirmed silent by production figures but carrying no `endDate` are flagged as informally ceased.

**Status values are clean.**
Unlike the UK NSTA data, which contains a misspelling (`Decomissioned`), NLOG status values are consistent, correctly spelled English terms. No corrections are required.

**The offshore filter must be applied in pandas.**
The NLOG datacenter UI offers an offshore filter but this cannot be relied upon when retrieving data programmatically. Apply `onOffshore == 'OFF'` explicitly after loading the data.

**No pagination required.**
All 6,723 records are returned in a single POST response. No offset or page-size logic is needed, unlike the UK NSTA API.

**Seven result codes referenced in prior documentation do not appear in the live dataset** (`SHW`, `INJ`, `OGS`, `STO`, `INC`, `CNS`, `GNS`). These are consistent with legacy codes retired during a data migration between DINO database versions. They do not affect the analysis — only codes present in the live data are used.

---

## Data Notes — Status and Result Code Reference

**Complete set of `statusDescription` values (offshore counts):**

| Status | Offshore count | Treatment |
|---|---|---|
| `Plugged and abandoned` | 1,316 | Exclude — decommissioning complete |
| `Producing/Injecting` | 266 | Exclude — active |
| `Monitoring` | 0 | Exclude |
| `Suspended` | 209 | Group A |
| `Closed-In` | 111 | Group A |
| `Sidetracked` | 249 | Group B |
| `null` | 44 | Ghost wells |

**`resultCode` values present in the live dataset:**

| Code | Meaning |
|---|---|
| `GAS` | Gas |
| `OIL` | Oil |
| `OAG` | Oil and associated gas |
| `GOS` | Gas, oil shows |
| `GSS` | Gas shows |
| `OLS` | Oil shows |
| `FLR` | Flared — hydrocarbons confirmed during testing |
| `GWOS` | Gas dominant, water present, oil shows |
| `OWGS` | Oil dominant, water present, gas shows |
| `WTR` | Water |
| `WTS` | Water shows |
| `DRY` | Dry — nothing found |
| `COAL` | Coal |
| `SALT` | Salt |
| `UNK` | Unknown |
| `null` | Not recorded |

The hydrocarbon filter used in Group A analysis includes: `GAS`, `OIL`, `OAG`, `GOS`, `GSS`, `OLS`, `FLR`, `GWOS`, `OWGS`.

---

## Analytical Framework

Wells are retrieved from the NLOG API and filtered to offshore only (`onOffshore == 'OFF'`), giving 2,195 offshore wells. These are then divided into analytical groups.

**Group A — Inactive offshore wells (core investigation population)**

`statusDescription in ['Suspended', 'Closed-In'] AND onOffshore == 'OFF'`

These are wells that have formally stopped operating but have not been plugged and abandoned. They are the population for which decommissioning liability is most immediate. Both statuses indicate a well capable of reactivation but not currently producing.

**Group B — Sidetracked offshore wells**

`statusDescription == 'Sidetracked' AND onOffshore == 'OFF'`

A sidetrack is a second borehole drilled at an angle from an existing well. The original borehole may be inactive while the sidetrack continues producing. Treated as a secondary population requiring case-by-case examination.

**Ghost wells — null status offshore**

`statusDescription == null AND onOffshore == 'OFF'`

44 offshore wells with no formal status classification. All 44 were drilled between 2021 and 2026, indicating data lag for recently drilled wells rather than old unclassified legacy wells. Documented separately and monitored for status assignment.

**Excluded entirely:**

`statusDescription in ['Plugged and abandoned', 'Producing/Injecting', 'Monitoring']`

---

## Project Structure

```
dutch-north-sea-decom/
├── pipeline_nl.py              -- entry point, runs the full pipeline end to end
├── netherlands/
│   ├── src/
│   │   ├── __init__.py
│   │   ├── fetch_nl.py         -- POST requests to NLOG boreholes and production APIs
│   │   ├── clean_nl.py         -- date conversion, operator field comparison, status filtering
│   │   └── analyse_nl.py       -- group splits, production crosscheck, ownership transfer analysis
│   ├── notebooks/
│   │   └── explore_nl.ipynb    -- interactive development notebook
│   ├── data/
│   │   ├── raw/                -- data as fetched, never modified
│   │   ├── processed/          -- cleaned and intermediate outputs
│   │   └── state/              -- hash files for change detection
│   └── outputs/
│       └── nl_wells_analysis.csv  -- final ranked output table
├── pyproject.toml              -- uv dependency management
└── .gitignore
```

The `netherlands/data/` directory is gitignored and is not included in this repository. It is recreated by running the pipeline.

---

## Setup

This project uses Python 3.13 and `uv` for dependency management.

**1. Install uv** if you do not have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**2. Clone the repository:**

```bash
git clone https://github.com/TomBrown4444/dutch-north-sea-decom.git
cd dutch-north-sea-decom
```

**3. Create the virtual environment and install dependencies:**

```bash
uv venv
source .venv/bin/activate
uv sync
```

**4. Create the data directories** (gitignored, not included in the repo):

```bash
mkdir -p netherlands/data/raw netherlands/data/processed netherlands/data/state netherlands/outputs
```

**5. Create a `.env` file** in the project root for email notifications (optional — pipeline runs without it):

```
EMAIL_ADDRESS=your@email.com
EMAIL_PASSWORD=your_app_password
NOTIFY_ADDRESS=notify@email.com
```

---

## Running the Pipeline

```bash
python pipeline_nl.py
```

This will:

- Initialise a session with the NLOG datacenter
- POST to the boreholes endpoint and retrieve all 6,723 well records
- Save raw JSON to `netherlands/data/raw/`
- Filter to offshore wells and split into Group A, Group B, and ghost wells
- Retrieve production figures and cross-reference against Group A
- Identify ownership transfers where `clientOrgName` differs from `legalOwnerName`
- Produce a ranked operator summary saved to `netherlands/outputs/nl_wells_analysis.csv`
- Run a sense check verifying all totals against expected values
- Hash the fetched data, compare to previous run, and send email notification if changed

---

## Using the Notebook

The notebook at `netherlands/notebooks/explore_nl.ipynb` was used to develop and validate each stage of the pipeline interactively. It is the best place to understand what the data looks like at each step and to experiment with additional analysis.

Open in VS Code by clicking `explore_nl.ipynb` in the sidebar. Select the `.venv` kernel when prompted — it will appear as `Python 3.13.x ('.venv': uv)`. If it does not appear, run `uv add ipykernel` in your terminal and restart VS Code.

The notebook is divided into seven sections. **Run them in order** — each section depends on variables set by the previous one. If you restart the kernel, run all cells from the top.

| Section | Description |
|---|---|
| 1 — Fetch | Initialises session, POSTs to NLOG API, prints first record, confirms field names |
| 2 — Inspect | Loads into pandas, prints shape, unique statuses, null counts, offshore vs onshore split |
| 3 — Filter | Applies offshore filter, splits into Group A / B / ghost, confirms totals match expected counts |
| 4 — Operator analysis | Groups by `clientOrgName` and `legalOwnerName`, flags transfers, ranks by inactive well count |
| 5 — Production crosscheck | Fetches production data, identifies confirmed-inactive and informally-ceased wells |
| 6 — Join and summarise | Combines all analysis into final ranked output table |
| 7 — Sense check | Verifies totals against pre-analysis console queries, flags any discrepancy |

---

## Verification

Offshore totals and group counts were independently verified before analysis by running direct queries against the live API from the browser console on `https://www.nlog.nl/datacenter/brh-overview`. Pipeline outputs match these independent counts exactly:

| Metric | Expected | Actual | Status |
|---|---|---|---|
| Offshore total | 2,195 | 2,195 | ✓ |
| Group A | 320 | 320 | ✓ |
| Group B | 249 | 249 | ✓ |
| Ghost wells | 44 | 44 | ✓ |

---

## Known Limitations and Next Steps

**No published non-compliance table exists.**
Unlike the UK investigation, there is no Dutch regulatory document to sense-check operator-level findings against. Operator totals must be verified directly against SodM annual inspection reports at `https://www.sodm.nl/publicaties`.

**Production data available from 2003 only.**
Wells that ceased production before January 2003 cannot be cross-checked against production figures. Cessation dates for these wells rely solely on the `endDate` field in the borehole record.

**KvK and UBO verification outstanding.**
The pipeline identifies operators and legal owners by name but does not yet trace ultimate beneficial ownership. Cross-referencing named entities against the Dutch commercial register (Kamer van Koophandel) and the UBO register is the critical next step for the accountability layer — particularly for operators identified as having received large numbers of transferred wells.

**Financial capacity assessment outstanding.**
Where legal owners are listed companies, their filed accounts should be reviewed for decommissioning provisions adequate to cover their identified liability. This applies particularly to smaller independent operators and to any entities identified as recently incorporated or thinly capitalised.

**Ghost well status monitoring.**
All 44 ghost wells were drilled between 2021 and 2026. Those drilled in 2021 and 2022 that still carry no status after three or four years warrant specific follow-up with NLOG or the relevant operator.

> **Disclaimer:** This is a preliminary dataset. No findings from this pipeline should be published without independent verification of operator names, ownership structures, and financial capacity.

---

## Data Licence

NLOG borehole and production data is published by TNO on behalf of the Dutch Ministry of Economic Affairs and Climate Policy and is freely accessible for public use. All source data is retrieved from live government APIs and is fully reproducible. No proprietary or licensed data has been used.

Code in this repository is released under the MIT Licence.

---

## Contact

Tom Brown  
GitHub: [TomBrown4444](https://github.com/TomBrown4444)
