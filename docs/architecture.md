# Architecture

Client → Nginx gateway → read/write FastAPI containers → shared PostgreSQL; redirects also use Redis. The gateway serves static HTML/CSS/JS. Local and GCP use the same Compose topology, all on one host.

## Boundaries
- `app.write:app`: register/login/me, link mutations, sequence allocation, cache invalidation; initializes schema at startup.
- `app.read:app`: owner-filtered listing, public metadata lookup, public 302 redirects.
- `app/common.py`: DB pool, Redis client, schema lifespan, link validation, active-user dependency, serialization and health.
- `app/auth.py`: Argon2id hashing, HS256 JWT issue/validation. Both services verify protected requests independently.
- `gateway/nginx.conf`: GET/HEAD link requests to read; other link methods to write; auth to write; redirects to read. Docker DNS resolution permits container replacement.

Write readiness precedes read startup so schema exists. At runtime read never calls write. Both share code, DB credentials and tables: this is a service split with shared storage, not fully isolated databases.

## Data
`users`: identity BIGINT primary key, unique normalized email, password_hash, created_at, is_active.
`urls`: code TEXT primary key, original_url, created_at, nullable expires_at, nullable created_by FK users(id). Owner/creation/code index supports listing. Legacy unowned links remain public.
`url_counter`: PostgreSQL sequence starting at 100000; Base62 alphabet `0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ`. Unique code constraint resolves alias races; generated codes retry collisions up to 20 times. Gaps and predictable codes are intentional.

## Request flows
- Register hashes password and inserts user; login verifies password; both issue JWT with subject, issued-at, expiry, issuer and audience. JWT default lifetime 30 minutes; protected endpoints also query active user.
- Create validates input and inserts with authenticated owner ID. Update/delete match code AND owner; mismatches return 404. Writes commit before cache invalidation.
- Redirect checks `bitly:link:{code}` then DB on miss. Cache stores destination/expiry for at most 30 seconds, bounded by remaining lifetime; expiry is checked on hits too. Redis errors fall back to DB. Redirect returns 302 with `Cache-Control: no-store`.
- Metadata always queries DB. Expired metadata/redirect returns 410; owner listing includes expired rows. No automatic expiry deletion.

## Failure and security limits
Concurrent cache refill or failed invalidation can serve stale destinations until the 30-second entry TTL expires. Cached redirects can survive DB outage, but authenticated lists require DB. Health requires DB and reports cache failure without failing health; gateway checks both backends.
One host is one failure domain. PostgreSQL persists in a Docker volume on the VM disk; Redis has no persistence. No HA, automated backups, TLS termination, refresh tokens, password recovery, email verification or auth rate limiting is implemented. Browser JWT is memory-only. Use an SSH tunnel for cloud credentials; predictable public codes are not access tokens.
