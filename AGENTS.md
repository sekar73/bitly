# Bitly project guide

## Read narrowly
- Start here. For implementation work, read `docs/feature-map.md`, then only the files relevant to the request.
- Read `docs/architecture.md` for cross-service changes; `docs/decisions.md` before changing established tradeoffs; `docs/deployment.md` for infrastructure work.
- Read `docs/status.md` only for current handoff context. Source/configuration wins if documentation disagrees; correct the relevant doc.
- Do not load the entire README, repository, lockfiles or generated output by default. Use scoped `rg` searches and bounded file reads; summarize large logs.
- Never read or print `.env`, real tfvars, Terraform state/plans, database dumps or private keys unless essential and explicitly authorized. Use examples for configuration discovery.

## Project constraints
- Learning URL shortener; plain HTML/CSS/JS frontend, Python FastAPI, PostgreSQL and Redis. Keep changes small and understandable; no new framework/dependency without a concrete need.
- GCP is the active cloud. `infra/gcp/` and `scripts/gcp-*.sh` are authoritative. Root `infra/` Terraform/bootstrap and `scripts/aws-*.sh` are legacy; do not extend them for ordinary work.
- Five Compose services: gateway, read, write, postgres, redis. Only gateway publishes an app port. PostgreSQL is durable truth; Redis is disposable.
- Preserve JWT checks, active-user checks and ownership predicates for link management. Public metadata/redirects are intentional. Keep credentials out of Git and responses.
- Preserve data on ordinary redeploy. Do not purge volumes, destroy cloud infrastructure or run global prune as incidental cleanup. Review infrastructure plans for replacement/data loss.

## Validation and completion
- Run the smallest meaningful existing check for the change. Frontend auth: `node tests/frontend-auth.js`; live API: `./scripts/test.sh` with Compose running.
- Run `./scripts/test-isolation.sh` only for service/gateway availability changes and when disrupting the local stack is acceptable. It stops backends briefly.
- GCP Terraform: `terraform -chdir=infra/gcp fmt -check` and `validate` after provider initialization. No deploy/destroy merely to validate a code edit.
- Do not rerun passing checks without a changed input or unresolved concern. Documentation-only edits need link/content checks, not a full live suite.
- Update only affected reference docs. Record new durable tradeoffs in decisions; keep status short, current and free of secrets. Do not copy chat history into docs.
- Final response: outcome, relevant checks, remaining limitations. Never imply cloud deployment or testing happened without evidence.

## Working efficiently
- Prefer one focused task at a time and existing project patterns. Ask only for missing decisions that materially affect implementation.
- Keep tool output bounded; avoid repetitive status polling and repository-wide dumps. Do not add speculative abstractions or tests that mirror trivial code.
- Respect user instructions over this guide. This workflow reduces repeated context; it cannot guarantee a token count or monetary saving.
