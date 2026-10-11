# Feature map

Use this index before searching broadly. Paths are relative to the repository root.

| Task | Start with | Existing verification |
|---|---|---|
| Register/login/JWT/password rules | `app/auth.py`, `app/write.py`, `app/common.py:current_user` | `tests/integration.py` |
| Link create/alias/code allocation | `app/write.py:create_link`, `app/common.py:Link,base62` | integration |
| Owner list/update/delete | `app/read.py:list_links`, `app/write.py`, `app/common.py:current_user` | integration |
| Redirect/cache/expiration | `app/read.py`, `app/common.py:invalidate` | integration; isolation for outage changes |
| Schema/database lifecycle | `app/common.py:lifespan`, `compose.yaml` | integration; plan migration for existing data |
| Browser UI/session handling | `app/static/app.js`, `index.html`, `style.css` | `node tests/frontend-auth.js` for auth; browser check for layout |
| Gateway routes/health | `gateway/nginx.conf`, `gateway/Dockerfile`, `compose.yaml` | integration; `scripts/test-isolation.sh` |
| Local setup/pgAdmin | `scripts/local-deploy.sh`, `local-destroy.sh`, `compose.local.yaml`, `.env.example` | local health; README pgAdmin section |
| GCP resources/bootstrap | `infra/gcp/main.tf`, `bootstrap.sh`, `terraform.tfvars.example` | Terraform fmt/validate |
| Cloud deployment/cleanup | `scripts/gcp-deploy.sh`, `gcp-destroy.sh`, `docs/deployment.md` | shell syntax; review plan before cloud actions |
| API examples/manual testing | `postman/README.md`, collection/environment JSON | import or JSON parsing |
| User-facing setup/costs | `README.md` | links/content; verify current pricing if revising figures |

## API contract summary
Public: POST `/api/auth/register`, POST `/api/auth/login`, GET `/api/links/{code}`, GET `/s/{code}`, health/docs.
JWT: GET `/api/auth/me`, GET `/api/links?offset=0`, POST `/api/links`, owner-only PUT/DELETE `/api/links/{code}`.
Link body: `original_url`, optional `alias`, optional timezone-aware future `expires_at`. PUT replaces destination/expiry; omitted expiry clears it. Alias is immutable. Listing pages contain at most 100 rows.
Errors: 401 invalid/missing auth, 404 missing/non-owned mutation, 409 duplicate email/alias, 410 expired public lookup, 422 invalid input, 503 failed creation/ID exhaustion.

Test wrappers: `scripts/test.sh` → `tests/integration.py`; `scripts/test-isolation.sh` → `tests/isolation.py`. Live tests create data; custom remote base URLs retain test users. Read the test before running against shared environments.
