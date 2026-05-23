# Dutch North Sea Decommissioning Investigation

A data pipeline that builds the operator accountability table that does not yet publicly
exist in the Netherlands — identifying which companies are sitting on inactive offshore
wells with no decommissioning programme, and how long those wells have been idle.

---

## The Story

When an oil or gas well stops producing, the operator is legally required to decommission
it: plug the wellbore with cement, remove the subsea infrastructure, and restore the
seabed. In the UK, the North Sea Transition Authority (NSTA) publishes a public table
showing which operators are behind schedule. **The Netherlands has no equivalent.**

This pipeline creates that table from scratch using two public datasets.

### Why it matters

**EBN** (Energie Beheer Nederland — the Dutch state energy company) holds a statutory
40% share in every upstream oil and gas licence in the Netherlands. This means that
roughly 40% of every decommissioning bill ultimately falls on the Dutch taxpayer by law.
Delayed decommissioning is therefore not just a regulatory problem — it is a direct
fiscal liability for the Dutch state.

The regulatory body is **SodM** (Staatstoezicht op de Mijnen — the Dutch mining
inspectorate). SodM publishes annual compliance reports, but these are PDFs, not
structured data, and do not contain a ranked operator table.

---

## What We Found

Analysis of 6,723 Dutch wells identified **320 inactive offshore wells** across 57
operators with no completed decommissioning programme.

| Legal owner | Inactive wells | Mean years idle | All inherited? |
|---|---|---|---|
| Eni Energy Netherlands B.V. | 109 | 33 years | Yes |
| Tenaz Energy Netherlands B.V. | 67 | 33 years | Yes (ex-Shell/NAM) |
| TotalEnergies EP Nederland B.V. | 48 | 30 years | Yes |
| TAQA Offshore B.V. | 27 | 31 years | Yes (ex-Amoco/BP) |
| Wintershall Noordzee B.V. | 19 | 25 years | Partial |

**91% of inactive wells (290 of 320) have been transferred** from the original operator
to a different legal owner. The company that drilled the well is almost never the company
that now owes the decommissioning bill.

**24 wells** are confirmed inactive by production data — zero output for two or more
consecutive years — despite remaining in formal "Suspended" or "Closed-In" status with
no decommissioning programme started.

**Tenneco Netherlands Inc.** holds 7 wells idle for an average of 53 years. Tenneco
sold its oil business in the 1980s; this Dutch subsidiary appears dormant, and no other
entity has assumed formal legal ownership.

**44 ghost wells** — recently drilled (2021–2026) with no status classification yet —
are concentrated among ONE-Dyas, Petrogas, Neptune, and Dana. These may tip into the
inactive category without ever appearing in a compliance table.

---

## Glossary

**Borehole / well** — a hole drilled into the seabed to reach an oil or gas reservoir.
The words are used interchangeably in Dutch regulatory data.

**Suspended** — the well has been temporarily shut in but not permanently abandoned.
Technically awaiting a decision on future use or decommissioning.

**Closed-In** — similar to Suspended; the well is sealed at the surface but the
wellbore is intact underground. Also awaiting a decommissioning decision.

**Plugged and abandoned (P&A)** — the well has been permanently decommissioned:
cement plugs seal the wellbore, infrastructure is removed. This is the end state.
P&A wells are excluded from the investigation.

**Sidetracked** — a new borehole drilled from a point partway down an existing well,
usually because the original path encountered a problem. Sidetracked wells can be
left in limbo if the programme that created them was abandoned.

**Ghost well** — a well in the NLOG dataset with no status code assigned. All 44
ghost wells in this dataset were drilled in 2021 or later and are likely pending
classification.

**resultCode** — NLOG's code for what the well found: `GAS` (gas), `OIL` (oil),
`DRY` (nothing commercially viable), `FLR` (shows of gas/oil but not commercial),
`OAG` / `OLS` / `GOS` / `GSS` / `OWGS` / `GWOS` (various mixed hydrocarbon results).

**clientOrgName** — the operating company: who drilled the well and whose name is on
the licence as operator of record.

**legalOwnerName** — the current licence holder: who is legally responsible for
decommissioning today. These diverge when a licence is sold or transferred.

**EBN** — Energie Beheer Nederland. Dutch state company that holds a mandatory 40%
interest in all upstream Dutch licences. EBN does not operate wells itself but
co-funds everything, including decommissioning.

**SodM** — Staatstoezicht op de Mijnen. The Dutch mining inspectorate. Publishes
annual compliance reports at https://www.sodm.nl/publicaties (PDFs only, not
structured data).

**NLOG** — Nederlands Olie en Gas (the Dutch oil and gas data portal at nlog.nl).
Operated by TNO on behalf of the Dutch government. The primary source for both
datasets used in this pipeline.

**Informal cessation** — a well where no formal cessation date is recorded but
production data confirms zero output for two or more consecutive years. These
wells are inactive in practice but have not been formally closed in the regulatory
record.

---

## Data Sources

### Dataset 1 — NLOG Borehole Data
- **URL:** `https://www.nlog.nl/nlog-mapviewer/rest/brh/boreholes`
- **Method:** POST (empty body) — requires a session cookie seeded by a prior GET
  to `https://www.nlog.nl/datacenter/brh-overview`
- **Returns:** 6,723 wells in a single JSON array (no pagination)
- **Updated:** Daily
- **Authentication:** None — fully open

### Dataset 2 — Production Figures Per Well
- **URL:** `https://www.nlog.nl/nlog-mapviewer/rest/prodfigures/well`
- **Method:** POST with body `{"yearStart": N, "yearEnd": N, "product": "Gas"|"Oil", "production": "Produced"}`
- **Returns:** Monthly production figures per well for the requested year
- **Available from:** 2003 only (pre-2003 data not in public domain)
- **Authentication:** None — same session cookie as Dataset 1

---

## Repository Structure

```
dutch_decom/
├── netherlands/
│   ├── pipeline_nl.py          # entry point — run this
│   ├── src/
│   │   ├── fetch_nl.py         # API calls and raw data saving
│   │   ├── clean_nl.py         # loading, date conversion, group filtering
│   │   └── analyse_nl.py       # operator tables, crossref, accountability table
│   ├── notebooks/
│   │   └── explore_nl.ipynb    # exploratory notebook — all seven analysis sections
│   ├── data/                   # gitignored
│   │   ├── raw/                # raw JSON from NLOG APIs
│   │   ├── processed/          # intermediate CSVs
│   │   └── state/              # pipeline state (hash checks etc.)
│   └── outputs/                # final deliverables
│       ├── nl_wells_analysis.csv       # accountability table by legal owner
│       └── nl_wells_by_operator.csv   # reference table by operator
└── README.md
```

### Output files

**`nl_wells_analysis.csv`** — the primary accountability table. One row per legal
owner. Columns: `legalOwnerName`, `inactive_well_count`, `mean_years_inactive`,
`max_years_inactive`, `confirmed_inactive`, `transferred_wells`, `result_codes`,
`earliest_spud`, `ghost_wells`.

**`nl_wells_by_operator.csv`** — same data grouped by `clientOrgName` (operator).
Note: operator names are not normalised in the NLOG source data. Multiple name
variants for the same company (e.g. "Placid", "Placid International Oil, Ltd.",
"Placid International Oil Ltd.") will appear as separate rows.

**`group_a_by_operator.csv`** — detailed well-level operator table (processed/).

**`informal_cessation_wells.csv`** — wells confirmed inactive by production
crossref (processed/).

**`ownership_transfers.csv`** — all wells where operator ≠ legal owner (processed/).

---

## Setup and Usage

### Requirements

- Python 3.11+
- `pip install requests pandas python-dotenv`

### Run the full pipeline

```bash
cd dutch_decom
python netherlands/pipeline_nl.py
```

This will:
1. Seed an NLOG session and fetch all boreholes (~6,700 records)
2. Fetch Gas and Oil production for 2020–2025 (12 API calls)
3. Filter offshore wells, split groups, run analysis
4. Write CSVs to `netherlands/data/processed/` and `netherlands/outputs/`

### Re-run analysis without re-fetching

If the raw data files already exist and you just want to re-run the analysis:

```bash
python netherlands/pipeline_nl.py --skip-fetch
```

### Explore interactively

Open `netherlands/notebooks/explore_nl.ipynb` in Jupyter. The notebook contains
all seven analysis sections with inline explanations, intermediate print-outs,
and validation checks at each stage.

---

## Analytical Framework

### Group A — Inactive offshore wells (core story)
`statusDescription` in `{Suspended, Closed-In}` AND `onOffshore == OFF`

All result codes included. Non-hydrocarbon wells (dry holes, water wells) carry the
same decommissioning obligation as producing wells.

**Note:** The original spec included a hydrocarbon-only `resultCode` filter, but
this reduced the count from 320 to 237. Investigation of the 83 excluded wells
confirmed they were Suspended/Closed-In offshore wells with the same decommissioning
status as the hydrocarbon wells. The filter was dropped.

### Group B — Sidetracked offshore wells
`statusDescription == Sidetracked` AND `onOffshore == OFF`

249 wells. Secondary story — incomplete or abandoned mid-drill.

### Ghost wells
`statusDescription` is null AND `onOffshore == OFF`

44 wells, all drilled 2021–2026. Likely freshly drilled wells pending status
classification rather than old unclassified records.

### Excluded
`statusDescription` in `{Plugged and abandoned, Producing/Injecting, Monitoring}`

---

## Notes and Caveats

- **Operator name fragmentation:** `clientOrgName` is a free-text field in the NLOG
  source. The same company can appear under multiple name variants (particularly
  "Placid" entities and the GDF/Total/Elf corporate chain). Totals in the operator
  table undercount these entities. The legal owner table is not affected because
  `legalOwnerName` reflects current registered entities.

- **Production data availability:** the NLOG production API covers 2003 onwards only.
  Wells that ceased production before 2003 cannot be confirmed inactive via this
  method. The `endDate` field in the borehole data is the primary cessation indicator
  for older wells.

- **EBN share:** EBN's statutory 40% share applies to production licences. The exact
  liability split for individual decommissioning programmes requires licence-level
  data not available in the public NLOG dataset.

- **SodM compliance data:** SodM annual reports contain operator-level findings but
  are PDFs rather than structured data. They are noted here as a manual reference
  source and are not part of the automated pipeline.

---

## Related

- UK pipeline: see the `src/` directory in the parent project for the equivalent
  NSTA-based analysis of the British continental shelf.
- NSTA non-compliance table (UK): published at https://www.nstauthority.co.uk
- SodM annual reports (NL): https://www.sodm.nl/publicaties
