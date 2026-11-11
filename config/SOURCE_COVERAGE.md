# Source coverage and status

The source catalog lists research targets, not completed website scrapers.

## Implemented collection methods
- Arbeitnow public job API (enabled by default)
- RSS feeds, when a verified URL is added to `config/sources.json`
- Public Greenhouse job boards with verified board tokens
- Lever public boards with verified site identifiers
- SmartRecruiters public company feeds with verified company identifiers

The optional feeds are not enabled until valid identifiers are configured. These collectors still require live network validation.

## Not yet integrated
XING, StepStone, Indeed Germany, Bundesagentur für Arbeit, LinkedIn, most recruitment agencies and construction employer sites have no dedicated collectors. Their names in the catalog do not mean they are scraped.

Prioritize permitted official feeds/APIs, ATS public endpoints and site-supported job alerts. Do not evade site access controls, CAPTCHAs or rate limits.

## Configuration
Example source settings (replace placeholders only with verified live endpoints):

```json
{
  "arbeitnow": {"enabled": true, "pages": 3},
  "rss": [],
  "greenhouse": [],
  "lever": [],
  "smartrecruiters": []
}
```

Role profiles are managed via the Google Sheet's Role_Searches tab when connected, falling back to `config/role_profiles.json`. The Sheets tab will require setup before the first production run.
