# Application Center — Germany Job Search Engine

**Operational.** This GitHub Actions project searches selected German/European vacancy feeds and automatically saves newly discovered candidate jobs to the user's existing Google Sheets tracker. It does not submit applications.

## Open the live system

- [GitHub repository](https://github.com/njimaadahmedcivil-dot/application-center-job-automation)
- [Google Sheets Job Tracker](https://docs.google.com/spreadsheets/d/1JUKnCUmshWZpKV8-VOebJ-KNScMu9R45pf0j_crsD4w/edit)
- **Actions** tab → **Application Center Daily Job Search** for run history.

## What works and what does not

**Five channels responded successfully in live GitHub runs on 2026-11-11:**
1. Arbeitnow public API.
2. Nomado24 public German/EU remote/hybrid jobs API.
3. Berlin Startup Jobs public RSS feed.
4. AECOM SmartRecruiters public employer feed.
5. EURES public portal job search interface (community-documented, not a guaranteed official API).

Live combined fetch: **1,785 raw records**; latest EURES expansion saved **12 new** jobs in the tracker. The database has 34 discovery entries after these tests. Raw records are not automatically qualified or confirmed open on employer websites.

**Not yet directly scraped:** XING, StepStone, Indeed Germany, BA Jobsuche, Manpower, Randstad, Adecco, most individual German agency and employer sites. Several agencies are included indirectly in EURES results. See [full source coverage](config/SOURCE_COVERAGE.md). German job portals do not all provide sanctioned jobseeker search APIs. The BA unofficial interface was disabled after an incompatible live response.

**Available but not configured:** documented Adzuna Germany search API (requires free developer API credentials), plus public ATS collectors for Greenhouse, Lever, SmartRecruiters, Ashby, Recruitee, Workable and Personio. These must be configured and tested for each employer.

## Customize job searches in Google Sheets

Open **Role_Searches**. One row per job profile:

`profile_id | enabled | display_name | track | title_terms | notes`

Use `TRUE` or `FALSE` to switch profiles on/off. Add any new role with a unique ID, one of five allowed tracks (`Civil engineering`, `Logistics & supply chain`, `Project management`, `Operations`, `Other`), and job title terms separated by semicolons. Example: `teamleiter logistik;logistics team lead;schichtleiter logistik`. No Python edits are needed.

The same search profiles apply to every configured collector; query-based providers receive bounded search phrases derived from all active profiles.

## Automations

- Workflow: `.github/workflows/daily-jobs.yml`
- Daily target: **08:13 Berlin time** with daylight-saving awareness.
- Manual runs: any time in GitHub Actions.
- Runs also trigger on search-code/configuration changes committed to main (serialized to avoid simultaneous writes).
- All jobs are appended to the `Jobs` tab with `discovered` status; never change applications to `applied` automatically.
- Data quality flags highlight language B2/C1 requirements, driving licence and specialist software when mentioned. The initial score is heuristic only.

## Source monitoring

Check **Source_Health**, **Run_History**, and **Site_Coverage** tabs in the connected tracker. They differentiate:
- operational API responses and number of records retrieved,
- failed or disabled interfaces,
- the total new matches saved during each run,
- websites in the longer wish list but not directly integrated.

## Optional: activate Adzuna Germany

1. Create an Adzuna API developer account at https://developer.adzuna.com and obtain `app_id` and `app_key`.
2. GitHub → Settings → Secrets and variables → Actions → **New repository secret**.
3. Create repository secrets `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` with their respective values. **Never upload the keys as repository files.**
4. Change `"enabled": false` to `true` for `adzuna` in `config/sources.json`.
5. Check **Actions** and **Source_Health** for the first live fetch.
6. Observe Adzuna's personal-use/API quotation limits and attribution requirements.

## Privacy and limitations

- The service account credential stays in `GOOGLE_SERVICE_ACCOUNT_JSON` GitHub Actions secret. Never upload it or paste it into chat.
- **Make this repository Private** in Settings → General → Danger Zone; it was last observed as Public and the connected tool cannot change visibility.
- GitHub Actions scheduling is best effort; exact execution time is not guaranteed.
- Sources may change formats or block public access. Failures are logged; healthy sources continue.
- The deployed Apps Script dashboard is separate and reads this Google Sheet after a page refresh.
- An application is **never submitted** by this workflow. Confirm vacancy details, your qualifications, language requirements and work authorization before applying.
