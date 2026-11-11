# Application Center — German Job Search Automation Skill

## Goal
Maintain an ATS-aware Germany-wide job discovery and tracking process for civil engineering, logistics, procurement, construction project coordination and user-defined searches.

## Source of truth
Use the user's Project Instructions, current approved Saju CV, verified own civil/construction work and education. Never attribute Cytel or Parexel PMO experience to this candidate. No invented achievements, qualifications, German-language level or visa permissions.

## Existing connected spreadsheet
Google Sheet: https://docs.google.com/spreadsheets/d/1JUKnCUmshWZpKV8-VOebJ-KNScMu9R45pf0j_crsD4w/edit
The Jobs sheet is the authoritative application tracker, and the deployed dashboard reads from it. Read the user's current Role_Searches sheet to determine enabled role queries; create/update that tab separately as needed.

## Search roles
Allow roles to be added, disabled, enabled and renamed in the Google Sheet without changing Python source. Examples: junior civil engineer, logistics team lead, junior procurement, project coordinator, production planner, or entirely different roles.

## Source integrations
Arbeitnow is enabled by default. RSS, Greenhouse, Lever and SmartRecruiters collectors exist but require verified source identifiers/URLs. The >40 websites in config/source_catalog.json are research targets: do not claim they have working scrapers until each is implemented and live-tested. Prefer official APIs, public ATS endpoints, permitted feeds, job alerts and reliable search.

## Job evaluation
Check employer, vacancy URL, location, publication/current status, required German, driving licence, work rights, academic qualifications, tools and seniority. Evaluate transferable experience separately from specific experience, and be explicit about gaps. Deduplicate by normalized URL and employer/title/location. Write discovery entries with status discovered only; never mark applied unless the user confirms submission.

## Application workflow
When user selects a vacancy, inspect full job description, tailor the approved Saju single-column LaTeX CV (complete editable .tex and PDF when available), preserve original job titles and factual history. Draft cover letter only when requested.

## Automation
GitHub Actions runs the scheduled collector, uses a Google service-account JSON secret and writes only new vetted jobs to the connected Sheets Jobs tab. The private GitHub repository must never contain credentials. Website dashboard styling is separate Apps Script code; do not claim GitHub automation changes its UI.

## Status
The pipeline's automated tests are mocked unit tests, not evidence of live job-board availability or successful Google service-account authentication. Treat every new integration as unverified until its live first run succeeds.
