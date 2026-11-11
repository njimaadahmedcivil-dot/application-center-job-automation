# German job sources — precise integration status

## Tested end to end
- **Arbeitnow public API**: authenticated GitHub -> Google Sheets write confirmed by a live run on 2026-11-11. The API uses no user key; 5 pages per run are now configured.

## Enabled and awaiting next live check
- **Berlin Startup Jobs public RSS**: the endpoint publishes a public RSS feed. Full feed parsing and job quality need production verification. If the site errors, the job is skipped and the source-health tab records the error.
- **AECOM / SmartRecruiters**: employer jobs are publicly advertised at `jobs.smartrecruiters.com/AECOM2/`. The company API is configured; its responses need production verification. Feeds may cover international positions, so Germany filtering remains mandatory.

## Implemented source families, not configured with employer tokens
- RSS/Atom
- Greenhouse public boards (`board_token`)
- Lever public boards (`site`)
- SmartRecruiters public company boards (`company_id`)
- Ashby public boards (`board`)
- Recruitee public boards (`site`)
- Workable public boards (`account`)
- Personio public jobs XML (`tenant` and optional `domain`)

These adapters are covered by local mocked tests. They cannot return a particular company's jobs until its public feed identifier has been verified and added to `config/sources.json`.

## Research targets with no direct collector
XING, StepStone, Indeed Germany, Bundesagentur für Arbeit, LinkedIn and most German recruiting agencies / construction career pages in `config/source_catalog.json` are not individually scraped. They require approved feeds, public employer ATS, official alerts or individual integration work. The BA Jobsuche endpoint described by third-party projects is *unofficial*; do not treat it as a guaranteed supported API.

## Tracking in Google Sheets
- `Jobs`: actual discovered jobs (deduplicated; status discovered only).
- `Role_Searches`: user-defined searches, including entirely new roles, and ON/OFF controls.
- `Source_Health`: collector group, enabled status, last checked time, count fetched, error.
- `Site_Coverage`: full website catalog with candid per-site status.

## Source configuration example

```json
{
  "arbeitnow": {"enabled": true, "pages": 5},
  "rss": [],
  "greenhouse": [{"company":"Verified Employer","board_token":"verified-board-slug"}],
  "lever": [{"company":"Verified Employer","site":"verified-lever-slug"}],
  "smartrecruiters": [{"company":"Verified Employer","company_id":"VerifiedCompanySlug"}],
  "ashby": [{"company":"Verified Employer","board":"verified-ashby-slug"}],
  "recruitee": [{"company":"Verified Employer","site":"verified-recruitee-slug"}],
  "workable": [{"company":"Verified Employer","account":"verified-workable-slug"}],
  "personio": [{"company":"Verified Employer","tenant":"verified-personio-slug","domain":"de"}]
}
```

No CAPTCHA evasion, login bypass or unsupported automated mass scraping. A source is never marked production-verified solely because code or a domain has been configured.
