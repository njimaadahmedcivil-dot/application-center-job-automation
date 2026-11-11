# Application Center — Automated German Job Discovery

A private-use job-discovery adapter that runs in GitHub Actions and writes new vacancies to the user's existing Google Sheets tracker. The script never applies to jobs or marks applications submitted.

## Live integrated system
- GitHub repository: https://github.com/njimaadahmedcivil-dot/application-center-job-automation
- Google Sheets database: https://docs.google.com/spreadsheets/d/1JUKnCUmshWZpKV8-VOebJ-KNScMu9R45pf0j_crsD4w/edit
- Google Cloud service account stored ONLY in GitHub Actions secret `GOOGLE_SERVICE_ACCOUNT_JSON` (do not commit the JSON).
- Scheduled check approximately **08:13 Europe/Berlin**, with daylight-saving time handling. GitHub scheduled jobs are best effort and can be delayed.
- On changes to search code, workflow runs automatically on `main`, and you can start a manual run any time via **Actions**.

## Current job sources
**Proven earlier:** Arbeitnow public API, including successful job-to-Sheets synchronization on 2026-11-11.

**Additional configured sources awaiting live validation:** AECOM public SmartRecruiters board, Berlin Startup Jobs public RSS feed.

**Code implemented; employer identifiers still needed:** Greenhouse, Lever, SmartRecruiters, Ashby, Recruitee, Workable and Personio ATS feeds; standard public RSS feeds. See `config/SOURCE_COVERAGE.md`.

**Not directly integrated:** XING, StepStone, Indeed, Bundesagentur für Arbeit, LinkedIn, most agencies and construction-company portals. Those websites are cataloged as research targets, not falsely described as working scrapers. Use approved public feeds, partner APIs, employer ATS pages or official alerts. No CAPTCHAs, login or rate-limit bypass.

## Google Sheets tabs
- `Jobs`: application records A:T, append-only discovery, no overwrites of existing applications.
- `Dashboard`: spreadsheet summary used by the deployed Apps Script site.
- `Role_Searches`: **add, edit, enable or disable ANY role** with no Python edit. Exact columns `profile_id | enabled | display_name | track | title_terms | notes`.
- `Source_Health`: date/time, enabled collector groups, returned records and errors (updated after each run).
- `Site_Coverage`: per-website catalog, whether it has real collector coverage, and next steps.

A new search profile means filtering *available collected records* by job titles, not magically adding a new job-board connection. Separate terms in `title_terms` using semicolons. Use one of the allowed tracks `Civil engineering`, `Logistics & supply chain`, `Project management`, `Operations`, `Other`. Leave job applications unsubmitted until user confirmation.

## Local checks
```sh
python -m pip install -r requirements.txt
python -m pytest -q
python job_search.py --dry-run
```
Mocked unit tests (17 locally passed) verify data extraction, civil-industry false-positive rejection, role switches, Google Sheet payloads and deduplication. Mock tests cannot prove any source currently returns live data. Actual source status is shown in the `Source_Health` tab after GitHub runs.

## Security and quality
- Keep repository **Private** (this must be configured in GitHub Settings by the repository owner if it is public).
- Never upload the service-account JSON or GitHub secrets to repository files or chat.
- The job-score number is a simple ranking heuristic, not probability of getting hired.
- Generic Project Engineer jobs outside civil/construction (e.g., medical devices) are screened out under civil profiles; other job profiles are user-configurable.
- Candidates must manually verify language thresholds, work authorization, driver's licence and skills before applying.
- The existing Apps Script dashboard UI is separate from this repository and is not altered by GitHub changes.

## Source list
See `config/source_catalog.json` (43 research targets), `config/sources.json` (active feeds) and `config/SOURCE_COVERAGE.md` (honest status).
