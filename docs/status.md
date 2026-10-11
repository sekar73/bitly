# Current handoff

Last reviewed: 2026-10-11. Keep this under roughly 40 lines; replace stale information rather than append session logs.

- Implemented: JWT users/ownership; link CRUD, aliases and expiry; cache-aside redirects; separate read/write containers and Nginx gateway; local/GCP Terraform deployment scripts; Postman collection.
- Active cloud: GCP. User previously reported healthy GCP read/write dependencies through an SSH tunnel. This is historical user evidence, not a current environment health check.
- Browser registration uses an explicit register click handler and login form submit; `tests/frontend-auth.js` covers that regression. Do not infer this local source was deployed remotely.
- No deployment, cloud billing verification or live runtime tests were performed for the documentation refresh.
- Known limitations/tradeoffs: see `architecture.md` and `decisions.md`. No new feature is automatically authorized by appearing there.
- Docs entry point: root `AGENTS.md`; feature navigation: `feature-map.md`; beginner setup/cost details: root README.

## Next handoff update
Record only: changed behavior, exact relevant files, checks actually run, unresolved blocker/next action. Avoid credentials, personal account details, full command output and conversation transcripts.
