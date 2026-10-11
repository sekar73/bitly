# Decisions

These describe implemented choices, not proposed features. Add a short entry only when a lasting tradeoff changes.

| Decision | Reason | Consequence / revisit when |
|---|---|---|
| Plain browser JS + FastAPI | Small learning stack, no frontend build tool | Add framework only for demonstrated UI complexity |
| Read/write containers with shared DB/code | Teach routing and independent process failures cheaply | Schema/credential coupling remains; split further for independent ownership/scaling |
| Nginx gateway on same host | One exposed app port; routes and static assets without managed gateway cost | Host failure affects everything; revisit with multiple hosts/TLS |
| PostgreSQL sequence + Base62 | Concurrency-safe durable counter, compact IDs | Predictable codes and gaps; range allocation only after measuring counter bottlenecks |
| Unique code primary key | DB resolves races for aliases and generated codes | Aliases global and immutable; generated codes retry occupied values |
| Redis cache-aside, 30-second TTL | Fast redirects and DB fallback with bounded entry lifetime | Stale redirects possible after mutation; strict revocation needs stronger coordination |
| JWT + active-user DB check | Stateless signed token and immediate disabled-user enforcement for management | Protected requests still depend on DB; no refresh-token flow |
| Public redirects AND metadata | Anyone can resolve shared links; authentication protects management | Short codes do not provide privacy; change API/security contract deliberately |
| Memory-only browser token | Avoid persistent token storage | Reload requires sign-in; logout clears local token, not server revocation |
| Startup schema setup by write | Simple initial setup and existing ownership-column addition | Not a full migration system; use versioned migrations before complex schema evolution |
| GCP single e2-micro + Docker DB/cache | Minimize lab infrastructure and illustrate architecture | 1 GiB memory and one failure domain; no automatic backups or HA |
| Project labels/names and explicit destroy script | Identify resources among learning projects | Terraform state must be preserved; deletion destroys cloud database |
| Manual project billing budget | Keep stack simple | Alerts are not a cap; user must configure/check them |

GCP replaces the earlier AWS deployment direction. Legacy AWS files remain only as historical implementation; do not use them as the current deployment guide.
