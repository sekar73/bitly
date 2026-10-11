# Deployment quick reference

For complete beginner steps, IAM, backups and dated pricing, read the corresponding sections in [README](../README.md). This file is a navigation/command reference, not a second pricing source.

## Local
Requires Docker Desktop/Compose and Python 3. From repository root:
```bash
./scripts/local-deploy.sh
./scripts/test.sh
node tests/frontend-auth.js # requires Node only for this optional test
docker compose ps
docker compose logs --tail=100 gateway read write
./scripts/local-destroy.sh # preserves database volume
```
URL `http://localhost:8000`; `.env` is generated on first deploy. `.env.example` lists settings. `--purge` on local-destroy deletes database data; use only intentionally. The pgAdmin override exposes only loopback PostgreSQL; see README.

## GCP
Sources: `infra/gcp/` and `scripts/gcp-*.sh`. Terraform >=1.6 and authenticated gcloud/ADC required; billing and Compute Engine API must be enabled. Copy `infra/gcp/terraform.tfvars.example` to ignored `terraform.tfvars`; set project_id and allowed_cidr to your connecting public IPv4 `/32`.

Defaults: us-central1/us-central1-a, Debian 12 e2-micro, 20 GB pd-standard auto-deleted boot/database disk, ephemeral public IPv4, dedicated VPC/subnet, SSH/HTTP restricted to allowed_cidr. VM/disk labels: project=bitly-lab, environment=learning, managed_by=terraform. Networking names and VM network tag identify this project. No managed DB/cache/load balancer.
```bash
./scripts/gcp-deploy.sh
```
Review plan before typing `deploy`. Upload includes app/gateway/build files, not local data/secrets; remote credentials are generated once. Existing remote `.env` and Docker volume survive ordinary reruns. Bootstrap installs Docker/Compose and adds swap. Infrastructure replacement can delete data; inspect every plan.

On your Mac, leave this tunnel running (replace project ID):
```bash
gcloud compute ssh bitly-lab --project=YOUR_PROJECT_ID --zone=us-central1-a -- \
  -N -o ExitOnForwardFailure=yes -L 127.0.0.1:8080:localhost:80
curl http://127.0.0.1:8080/health/read
curl http://127.0.0.1:8080/health/write
```
Open `http://127.0.0.1:8080`; Postman uses that base URL. Direct VM HTTP is unencrypted. Remote integration tests can use TEST_BASE_URL but retain accounts; isolation drill is local-only. Remote app files live at `/opt/bitly`; inspect containers with `sudo docker compose ps` there.

## Costs and lifecycle
Use README's dated cost table and official pricing links; do not assume Free Tier or credits remain available. Main billed components: VM, provisioned disk, public IPv4 and excess transfer. Budget alerts must be created manually and do not stop spending.
Stopping VM preserves disk/data and releases ephemeral IP; disk may still cost money. Starting may change IP. Refresh Terraform outputs if needed.
```bash
gcloud compute instances list --project=YOUR_PROJECT_ID
gcloud compute instances stop bitly-lab --project=YOUR_PROJECT_ID --zone=us-central1-a
gcloud compute instances start bitly-lab --project=YOUR_PROJECT_ID --zone=us-central1-a
./scripts/gcp-destroy.sh
```
Destroy requires reviewing plan and typing `destroy`; deletes VM/database disk and dedicated networking. Backup first if needed (README instructions). Project, billing link, enabled APIs, manual budget and unrelated resources remain. Failed deployment can leave billable resources. Preserve Terraform state until cleanup succeeds; never commit state, real tfvars, plans, secrets or dumps.
