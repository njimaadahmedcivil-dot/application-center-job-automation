# Implementation status (2026-11-11)

- Local tests: run `python -m pytest -q` (test status confirmed below in packaging).
- Implemented and runnable: Arbeitnow REST API, configured RSS feeds, configured Greenhouse public boards, configured Lever boards, configured SmartRecruiters company postings API. Non-Arbeitnow sources require verified company identifiers/feed URLs.
- Existing integration code: Google Sheets `Jobs` append + duplicate checks and user-managed `Role_Searches` filtering. Requires service-account setup and permission.
- Site registry: over 40 research targets, clearly flagged where not implemented. Direct collectors for XING, StepStone, Indeed, Arbeitsagentur, agency websites are NOT present.
- No live external fetching or real Google authorization was possible in local offline tests.
- GitHub Actions workflow is included, awaiting user repository upload and secret setup.
- Job applications are never auto-submitted.
