# Application Center — Germany-wide job search automation (GitHub-ready)

**This ZIP is the complete uploadable repository package.** It contains initial runnable collectors, Google Sheets synchronization, configurable job-role switches, and an explicit German website source registry. It does **not** claim that every website in the registry can be directly scraped. See [Source coverage](config/SOURCE_COVERAGE.md).

# Application Center — Germany Job Discovery to Google Sheets

This repository is a **new runnable Python adapter**, designed around the user's uploaded MIT-licensed `ai-job-search` project. It does **not** claim to execute that project's Claude Code agents, nor to scrape the 42 sites in the German skill catalog. `config/PROJECT_SKILL.md` preserves the adapted search and CV rules. See upstream copyright in `UPSTREAM_LICENSE.txt`.

## What works in this adapter

- A public-data collector for the **Arbeitnow job API** (up to 5 pages per run).
- Optional feed collector for URL-provided public **RSS/Atom** job feeds.
- Optional public **Greenhouse** jobs API collector for configured employer board tokens.
- German civil engineering and logistics keyword triage, obvious senior-role filtering, transparent provisional score, language/licence red flags.
- Deduplication based on canonical link and company/title/location, against existing **Jobs** rows.
- **Append-only** writes into the *existing* 20-column `Jobs` tab, with `discovered` status only. Never modifies applied/interview statuses.
- GitHub Actions tests and a schedule targeted at 08:00 Europe/Berlin (DST-aware check).
- **Customizable job roles:** reads `Role_Searches!A1:F200` in your existing Google Sheet on every live run. Enable/disable or add any job title with semicolon-separated search terms; no Python changes required. These profiles filter collected vacancies rather than causing every job website to be searched for the keywords.

**Not implemented:** direct XING/StepStone/Indeed/Arbeitsagentur/Randstad/Manpower/Adecco scrapers or official APIs; fully verified 42-source coverage; employer-site validation; AI reasoning/ATS score; auto-application; email alerts. Names in the skills catalog are **research targets**, not functioning collectors.

## Set up (10–25 minutes, requires your own Google/GitHub access)

1. Create a **private GitHub repository**. Upload the contents of this folder to its root (keep `.github/workflows/daily-jobs.yml`). Do not upload your CV, passport, photo or credentials.
2. In Google Cloud Console create/select a project, **enable the Google Sheets API**, create a **service account**, and generate a JSON key. Follow your organization's security policy. A service-account JSON key gives programmatic access to sheets you share with it; handle carefully.
3. Open [your existing job tracker](https://docs.google.com/spreadsheets/d/1JUKnCUmshWZpKV8-VOebJ-KNScMu9R45pf0j_crsD4w/edit), click **Share**, and give the service account's `client_email` **Editor** access. Do not make the sheet public.
4. In GitHub repo **Settings → Secrets and variables → Actions → New repository secret**, enter `GOOGLE_SERVICE_ACCOUNT_JSON` and paste the **entire** service-account JSON (as the secret value; do not commit it). Your repo must stay private.
5. In the existing Google Sheet, create a tab called `Role_Searches` with these EXACT columns in A1:F1: `profile_id`, `enabled`, `display_name`, `track`, `title_terms`, `notes`. Copy the starter profiles from `config/role_profiles.json` in their listed order. Track must be one of: `Civil engineering`, `Logistics & supply chain`, `Project management`, `Operations`, `Other`. Separate title terms with semicolons. `enabled` accepts TRUE/FALSE, yes/no, or 1/0. The automation reads this tab each time; it fails safely if the tab is absent or incorrectly labeled.
6. In GitHub **Actions → Application Center Daily Job Search → Run workflow** to test. Check logs for `new_saved` and confirm rows in the existing Jobs tab. Refresh your deployed dashboard afterward.
7. Keep `.github/workflows/daily-jobs.yml` enabled. It uses two UTC times (06:13 and 07:13), then a Europe/Berlin check ensures only the 08:00 local attempt runs. GitHub cron runs on a best-effort basis, may be late/skipped, and is not guaranteed precisely at 08:00.

### Source setup

`config/sources.json` enables the public Arbeitnow API by default. To add a *real*, working site integration (not merely a domain on a list):
- RSS: add `{"name":"Agency job RSS", "url":"https://EXACT-VALID-FEED-URL", "location":"Germany", "company":"Agency or employer"}` under `rss`. Only use a source that explicitly publishes a compatible RSS or Atom feed. Verify entry link/title/company quality before enablement.
- Greenhouse: add `{"company":"Employer name", "board_token":"actual_public_board_token"}` under `greenhouse`. The token must be confirmed from the employer's official job board; do not guess.
- StepStone, XING, Indeed, Manpower, Adecco and Randstad: **not wired to collectors yet**. Their official job alerts can provide coverage while specific integration permissions/data feeds are investigated. Do not bypass paywalls, logins, CAPTCHA, or robots/access controls.

### Try locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
pytest -q
python job_search.py --dry-run
```

The dry run fetches public job data only and doesn't need Google credentials; it uses local `config/role_profiles.json` rather than the live Google Sheet. Real Sheets writing needs the JSON secret: locally set `GOOGLE_SERVICE_ACCOUNT_JSON` in your shell (never commit or paste it into chat), then run `python job_search.py`.

### Safety and caveats

- The score is an explainable **keyword triage heuristic** (not hiring probability, not a rigorous review of eligibility). New entries should be human-checked before shortlisting or CV generation.
- A failed API source is logged; other sources continue. A completely empty fetch leaves your sheet unchanged. A valid service-account credential, Sheets permission and GitHub Actions setup **must be tested live by the user**.
- Duplicate prevention is read-then-append, not a database transaction. Avoid concurrent workflow runs; this workflow has one scheduled job. A future code upgrade should add rechecking or locking for concurrency.
- `Jobs` must retain the same A:T headers; changes cause a safe failure rather than corrupting the database.
- Your dashboard reflects appended rows after refreshing the browser. It is **not edited** by this code.
- Time zone matters: Google Sheet's spreadsheet timezone may be UTC, but this workflow sets dates based on Europe/Berlin explicitly.
