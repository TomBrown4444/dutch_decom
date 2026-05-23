# North Sea Decommissioning — Methodology

**Project:** North Sea Decom  
**Status:** Data collection and analysis complete. Journalistic verification in progress.  
**Scope:** United Kingdom Continental Shelf (UKCS) and Dutch Continental Shelf (NCS)  
**For:** Editorial review

---

## Overview

This document explains how this investigation was built, where the data comes from, and why the methodology is sound. It is written for an editorial audience and explains technical terms where they arise.

The investigation uses publicly available government data from two countries to examine the same question from two angles: which oil and gas operators are sitting on inactive offshore wells that have not been decommissioned, how long have those wells been inactive, and who is ultimately liable for the cost of cleaning them up?

Decommissioning refers to the process of permanently plugging and abandoning a well once it has finished producing — sealing it to prevent leaks, removing infrastructure, and restoring the seabed. In the North Sea this is a legal obligation under both UK and Dutch law. It is also expensive: the UK industry regulator estimates the total cost at £44 billion for UK waters alone.

The investigation does not rely on leaked documents, confidential sources, or non-public data. Every finding is derived from open government datasets that anyone can access. The value of the investigation is in combining datasets that have never been joined before, and asking questions of the data that the regulators themselves have not published answers to.

---

## Part One — United Kingdom

### The Regulatory Context

The North Sea Transition Authority (NSTA) is the UK regulator for oil and gas on the UK Continental Shelf. Under the Petroleum Act 1998 and the Energy Act 2016, operators holding licences to produce oil or gas are legally required to decommission wells once production ends. The NSTA issues consents — formal regulatory approvals — setting deadlines for each well's decommissioning. A well that has missed its consent deadline is described as "out of consent."

In December 2025 the NSTA published, for the first time, a table naming 13 operators that had collectively missed decommissioning deadlines on 153 wells. This was reported by trade publications including Energy Voice. No mainstream news outlet investigated it further at the time, and no one examined it at well level.

### What the NSTA Table Does Not Tell You

The NSTA's published table is an operator-level snapshot — it names companies and counts wells, but gives no information about which specific wells are affected, where they are, how long they have been inactive, or who ultimately owns the companies named. It also does not identify the larger population of wells that are inactive but not yet formally in breach — operators who are not yet on the NSTA's radar but whose well portfolios suggest they will be.

This investigation answers those questions.

### Dataset 1 — NSTA Well Data

**Source:** North Sea Transition Authority  
**Access:** Publicly available, no registration required  
**Format:** Live database accessed via a standard web API (an Application Programming Interface — a method of querying a database programmatically rather than downloading a file manually)  
**Endpoint:** `https://services-eu1.arcgis.com/OZMfUznmLTnWccBc/arcgis/rest/services/UKCS_offshore_wellbore_top_holes_(WGS84)/FeatureServer/0/query`  
**Records retrieved:** 5,065 suspended wells  
**Updated:** Live service

The NSTA maintains a public database of every well drilled on the UK Continental Shelf through its Well Operations Notification System (WONS). This database is accessible via an industry-standard mapping API and returns records in a machine-readable format (JSON — a standard data format used across the web).

Each well record contains the following fields used in this investigation:

| Field | Description |
|---|---|
| `TDOPERATOR` | The name of the operating company, as submitted by the operator to WONS. Stored in full legal name format, all uppercase. |
| `COMPLESTAT` | Completion status — describes the mechanical state of the well (e.g. whether abandonment work has begun and at what stage). |
| `WELLOPSTAT` | Operational status — describes whether the well is active, suspended, or decommissioned. |
| `SPUDDATE` | The date drilling began, stored as a Unix timestamp (a number representing milliseconds since 1 January 1970 — a standard date storage format that requires conversion to a human-readable date). |
| `WELLREGNO` | The well registration number — a unique identifier in the format used across the North Sea industry (e.g. `211/18-1`). |
| `geometry` | The geographic coordinates of the well's surface location, stored in WGS84 format (the same coordinate system used by GPS). |

**How the data was retrieved:** Because the API returns a maximum of 1,000 records per request, the pipeline makes multiple requests in sequence, incrementing the starting position each time, until all records have been retrieved. This is standard practice when working with large API datasets and is called pagination.

**A data quality note:** The word "Decommissioned" is misspelled throughout the NSTA database as "Decomissioned" (one m). All filters in the pipeline match this misspelling exactly. This is documented in the data diary and does not affect the accuracy of the results — it is simply a quirk of the source data.

### Dataset 2 — NSTA Non-Compliance Table

**Source:** North Sea Transition Authority  
**Access:** Publicly available on the NSTA website  
**URL:** `https://www.nstauthority.co.uk/regulatory-information/decommissioning/well-decommissioning/`  
**Format:** Table published on a web page, manually extracted to CSV  
**Records:** 22 operators listed

This is the table the NSTA published in December 2025 naming operators who have missed decommissioning consent deadlines. It contains five columns: operator name, total wells to be decommissioned, wells within consent, wells out of consent, and percentage in consent.

Because this table is published as a static document rather than a machine-readable dataset, it was manually extracted and saved as a CSV file (a simple spreadsheet format readable by any data analysis tool).

### How the Two UK Datasets Were Combined

The two datasets were joined on operator name — matching each well in the NSTA database to the corresponding operator row in the non-compliance table. This is technically straightforward but required significant manual work because operator names are recorded differently in the two sources. The NSTA database uses full legal names in uppercase as submitted by operators (for example, `NEO NEXT + ENERGY RESOURCES UK LIMITED`), while the non-compliance table uses shorter display names (`NEO Next`). A manual reconciliation dictionary was built by comparing the complete list of unique operator names from both datasets side by side.

Four operators in the non-compliance table — Total Energies, CalEnergy, Energean, and Petrogas — were not matched to their equivalents in the well database during this analysis. Their aggregate out-of-consent well count is included in the verified total of 153 but is not yet attributed at well level. Resolving these requires identifying the exact legal names used in WONS submissions and is noted as an outstanding task before publication.

### Analytical Framework — UK

Wells were filtered to those with operational status `Suspended` and a valid operator name. These were then divided into two groups:

**Group A — In decommissioning process but incomplete**  
Wells with completion status `Abandoned Phase 1` or `Abandoned Phase 2`. These are wells that have formally entered the abandonment process but have not finished it. When joined to the non-compliance table, these are the wells where out-of-consent designations are attributed.

**Group B — Plugged but not in any decommissioning programme**  
Wells with completion status `Plugged`. These wells have stopped producing and been physically plugged, but have not formally entered any abandonment programme. They do not appear in the NSTA's published non-compliance table because they have not yet breached a deadline. They represent the forward-looking liability — operators accumulating inactive wells with no decommissioning plan on record.

**Verification:** The pipeline's output was cross-checked against the NSTA's published figures. The total of 153 out-of-consent wells across 13 operators matches exactly. This sense check confirms the join logic is correct.

---

## Part Two — The Netherlands

### The Regulatory Context

The Dutch equivalent of the NSTA is SodM (Staatstoezicht op de Mijnen — the State Supervision of Mines). Operators are required to decommission wells under the Dutch Mining Act (Mijnbouwwet). Unlike the UK, the Netherlands has a structural feature that makes the taxpayer exposure more direct: EBN (Energie Beheer Nederland), a state-owned company, holds a statutory 40% share in virtually all Dutch oil and gas production licences. This means the Dutch state is automatically co-liable for a significant portion of decommissioning costs, regardless of what the operator does.

Crucially, the Netherlands has never published an operator-level non-compliance table equivalent to the NSTA's December 2025 disclosure. There is no Dutch equivalent document. This investigation therefore does not compare against a published standard — it builds the accountability picture from scratch using raw well data and production records.

### Dataset 1 — NLOG Borehole Data

**Source:** TNO (Netherlands Organisation for Applied Scientific Research) — Geological Survey of the Netherlands, on behalf of the Dutch Ministry of Economic Affairs  
**Portal:** `https://www.nlog.nl` (the Dutch Oil and Gas portal, known as NLOG)  
**Access:** Publicly available, no registration required  
**Format:** JSON data accessed via a web API  
**Endpoint:** `https://www.nlog.nl/nlog-mapviewer/rest/brh/boreholes`  
**Records retrieved:** 6,723 total wells (all jurisdictions); 2,195 offshore wells  
**Updated:** Daily

NLOG is the Dutch equivalent of the NSTA's public data portal. It is managed by TNO — the Netherlands Organisation for Applied Scientific Research — on behalf of the Dutch government and contains administrative records for every borehole drilled in Dutch territory and on the Dutch continental shelf.

Unlike the UK API, which returns records in pages of 1,000 requiring multiple requests, the NLOG API returns all 6,723 records in a single response. No pagination is required.

The API requires a specific type of request (a POST request, as opposed to a simple page visit) and a session cookie set by first loading the datacenter page. Both of these are standard web behaviours that the pipeline handles automatically using Python's `requests.Session()` — a tool that manages web sessions the same way a browser does.

Each well record contains the following fields used in this investigation:

| Field | Description |
|---|---|
| `boreholeName` | Full well name |
| `shortName` | Abbreviated well name |
| `clientOrgName` | The company that operated the well at the time of drilling |
| `legalOwnerName` | The current legal owner of the well — which may be a different company from the original operator |
| `statusDescription` | Current status of the well (e.g. Suspended, Closed-In, Plugged and abandoned) |
| `resultCode` | What the well found (e.g. GAS, OIL, DRY) |
| `onOffshore` | Whether the well is onshore (`ON`) or offshore (`OFF`) |
| `startDate` | Date drilling began — stored as a Unix timestamp, same format as the UK data |
| `endDate` | Date the well ceased operation — stored as a Unix timestamp |
| `confidentialityDate` | The date from which the well's data became public |
| `blockCd` | The licence block identifier |

**An important distinction from the UK data:** The NLOG data contains two separate operator fields — `clientOrgName` (the company that drilled and operated the well) and `legalOwnerName` (the company currently holding legal responsibility for it). In the UK data only a single operator field exists. The presence of both fields in the Dutch data makes it possible to identify wells where legal ownership has been transferred since drilling — a significant finding in its own right.

**Data quality:** Status values in the NLOG data are clean, consistently formatted English terms with no misspellings — a contrast to the UK data. Dates are stored in the same Unix millisecond format and require the same conversion.

### Dataset 2 — NLOG Production Figures

**Source:** NLOG / TNO  
**Endpoint:** `https://www.nlog.nl/nlog-mapviewer/rest/prodfigures/well`  
**Format:** Monthly production volumes per well, per year  
**Available from:** January 2003 (pre-2003 data not in the public domain)

Because the Netherlands has no published non-compliance table, this investigation uses a different approach to identify inactive wells: production data. Under Dutch law (Article 111 of the Mining Decree), operators are required to report monthly production figures to TNO within four weeks of each month's end. These figures are then published publicly within a further four weeks. The result is a near-real-time public record of what each well is producing month by month.

A well that stops appearing in production figures, or that shows zero production across consecutive months, has ceased producing — regardless of what its formal status record says. Cross-referencing status data against production data identifies wells where cessation is confirmed by two independent sources, and also identifies wells where `endDate` is absent from the status record but production data confirms the well has been silent for years. These are described in the analysis as "informally ceased" wells.

### Analytical Framework — Netherlands

All 6,723 records were retrieved and filtered to offshore wells (`onOffshore == 'OFF'`), giving 2,195 offshore wells. These were then divided into analytical groups:

**Group A — Inactive offshore wells (core investigation population)**  
Wells with `statusDescription` of `Suspended` or `Closed-In`. These are wells that have formally stopped operating but have not been plugged and abandoned. They are the Dutch equivalent of the UK's Group A and represent the population for which decommissioning liability is most immediate.

**Group B — Sidetracked wells**  
Wells with `statusDescription` of `Sidetracked`. A sidetracked well is one from which a second borehole has been drilled at an angle — the original borehole may be inactive while the sidetrack continues producing. These require case-by-case examination and are treated as a secondary population.

**Ghost wells**  
Wells with no `statusDescription` recorded (`null`). These have no formal operational classification in the public record.

**Excluded:**  
Wells with `statusDescription` of `Plugged and abandoned` (decommissioning complete), `Producing/Injecting` (active), or `Monitoring` (designated for subsurface observation only).

**Production crosscheck:** Group A wells were cross-referenced against production figures to identify those with confirmed zero output over recent years. This provides independent corroboration of inactivity beyond the status field alone, and identifies wells where the formal status record may be lagging behind operational reality.

**Ownership transfer analysis:** For each Group A well, `clientOrgName` and `legalOwnerName` were compared. Where these differ, the well's decommissioning liability has been transferred from the original operator to a different legal entity. The scale of this transfer across the Dutch dataset is a core finding of the investigation.

**Verification:** Offshore totals and group counts were verified against direct queries run against the live API before analysis began. All figures match.

---

## Data Pipeline — Technical Summary

The investigation is built as a reproducible Python data pipeline — a series of automated steps that retrieve, clean, join, and analyse the data. The code is version-controlled using Git (a standard tool for tracking changes to code) and stored in a private GitHub repository. Every step is documented and logged, and intermediate outputs are saved at each stage so any finding can be traced back to its source data.

The pipeline is structured so that any team member or independent verifier can clone the repository, run the code, and reproduce every output from the raw data sources. The only manual steps are the initial extraction of the NSTA non-compliance table (a static web document rather than a machine-readable dataset) and the operator name reconciliation dictionary.

**Libraries used:**

| Tool | Purpose |
|---|---|
| Python 3.13 | Programming language |
| pandas | Data cleaning, joining, and analysis |
| requests | Retrieving data from web APIs |
| python-dotenv | Managing credentials securely |
| pathlib | File path management |
| hashlib | Detecting when source data has changed between pipeline runs |

The pipeline includes a change detection function: each time it runs, it creates a fingerprint (called a hash) of the data it retrieved and compares it to the fingerprint from the previous run. If the data has changed, an email notification is sent automatically. This means the pipeline can be run on a schedule and will alert the team whenever the NSTA or NLOG updates their data — relevant if, for example, the NSTA publishes an updated non-compliance table.

---

## What This Investigation Does Not Claim

This document describes the data and methodology only. Journalistic findings, including named operators, specific well counts, and ownership conclusions, are being verified separately before publication and are not included here.

The following are outstanding verification tasks before any findings can be published:

- Operator name reconciliation for four unmatched UK operators (Total Energies, CalEnergy, Energean, Petrogas)
- Companies House verification of key operators' ultimate beneficial ownership and financial capacity
- Cross-referencing Dutch findings against SodM annual inspection reports
- Legal review of any ownership or liability claims
- Right of reply from all named operators

The data is preliminary. No finding from this pipeline should be treated as confirmed without independent journalistic verification.

---

## Data Licences

**NSTA well data** is published under the Open Government Licence v3.0, which permits reuse with attribution.

**NLOG borehole and production data** is published by TNO on behalf of the Dutch Ministry of Economic Affairs and is freely accessible for public use.

All source data is retrieved from live government APIs and is reproducible. No proprietary or licensed data has been used.

---

## Contact

Tom Brown  
GitHub: [TomBrown4444](https://github.com/TomBrown4444)
