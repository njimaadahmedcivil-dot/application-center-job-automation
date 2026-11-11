# German job-search source coverage — verified status, November 11, 2026

This repo is a real automated job-search pipeline. The `Site_Coverage` and `Source_Health` tabs in the connected Google Sheet are the operational source of truth.

## Live-tested and enabled sources

| Source | Collection method | Last known verified response | Coverage |
| --- | --- | --- | --- |
| Arbeitnow | Public documented API | 1,500 records per five-page run | Germany and Europe, multiple employers |
| Nomado24 | Public documented API | 37 records | German/EU remote and hybrid jobs; source attribution required |
| Berlin Startup Jobs | Public RSS | 12 records | Berlin-focused posts |
| AECOM | SmartRecruiters company public API | 200 records | International employer feed; only German matches retained |
| EURES | Community-documented public EU portal interface | 36 Germany-filtered records | German jobs imported from European employment services; limited city fields |

The verified combined live run returned 1,785 raw records and saved 12 additional matches; earlier runs also saved 16 new matches. Raw records are not verified applicant matches. Search results are append-only and recorded as `discovered`, never applied.

## Implemented, not enabled

- **Adzuna Germany:** officially documented API connector in `job_search.py` but needs Adzuna-issued `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` GitHub repository secrets. Set `"enabled": true` in `config/sources.json` only after registration and review of terms, attribution and API quota. Never commit credentials.
- Greenhouse, Lever, SmartRecruiters, Ashby, Recruitee, Workable and Personio: generic public career-board collectors. Their employer-specific identifiers must be discovered and checked before activating.

## Disabled after a failed live check

- **Bundesagentur für Arbeit**: community-documented, unsupported Jobsuche endpoint was queried but the returned response lacked the documented `stellenangebote` field. This connector is disabled in `config/sources.json`. Do not claim it is actively scraping the official agency portal. Many BA and agency jobs may nevertheless appear via the EURES feed.

## Cataloged, but NOT directly integrated

XING, StepStone, Indeed Deutschland, LinkedIn, meinestadt.de, Stellenanzeigen.de, Jobware, Kimeta, get in Engineering, ingenieur.de, academics.de, and recruitment companies such as Manpower, Randstad, Adecco and many construction firms. They are **research targets**, not fully implemented per-site scrapers. Some employers and agencies (e.g. FERCHAU, I.K. Hofmann) have already appeared through EURES, which is source coverage, not a working direct scraper on the agency website.

For sites with restrictions or no documented public jobseeker search API, use supported employer ATS feeds, sanctioned job alerts, or licensed job-search aggregators. Never circumvent account controls, CAPTCHAs or access restrictions.

## Role search and ranking

`Role_Searches` in Google Sheets is user-editable: enable, disable, rename or add any role and semicolon-separated keywords. The query-driven collectors (EURES, Nomado24, Adzuna, experimental BA) generate queries from active profiles. Other feeds deliver records that are title-filtered. Relevance scores are preliminary keyword heuristics, not a verified qualification assessment or odds of getting hired.

## Dashboard / data

- `Jobs` — 20-column master job tracker
- `Role_Searches` — configurable searches
- `Source_Health` — live collector counts and API errors
- `Run_History` — counts of matched and newly saved jobs
- `Site_Coverage` — catalog and real status
- Dashboard website — separately deployed Google Apps Script UI, refresh it to see database updates

Important: Source listing links, not applying to jobs. Review each live vacancy, employer, exact location, German and driving-license requirements before submitting an application.
