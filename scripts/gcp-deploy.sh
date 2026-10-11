#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[[ -f infra/gcp/terraform.tfvars ]] || { echo 'Configure infra/gcp/terraform.tfvars first.'; exit 1; }
terraform -chdir=infra/gcp init
terraform -chdir=infra/gcp fmt
terraform -chdir=infra/gcp validate
terraform -chdir=infra/gcp plan -out=plan
read -r -p 'Create the Google Cloud resources shown? Type deploy: ' answer
[[ "$answer" == deploy ]] || exit 1
terraform -chdir=infra/gcp apply plan
project=$(terraform -chdir=infra/gcp output -raw project_id)
zone=$(terraform -chdir=infra/gcp output -raw zone)
instance=$(terraform -chdir=infra/gcp output -raw instance_name)
ready=false
for attempt in {1..60}; do
  if gcloud compute ssh "$instance" --project="$project" --zone="$zone" --quiet --command='test -f /opt/bitly/bootstrap-ready'; then ready=true; break; fi
  sleep 10
done
[[ "$ready" == true ]] || { echo 'Bootstrap failed. Resources remain; inspect serial logs or run gcp-destroy.sh.'; exit 1; }
tar -czf .bundle.tar.gz app gateway requirements.txt Dockerfile compose.yaml .dockerignore
gcloud compute scp .bundle.tar.gz "$instance:/tmp/bitly-bundle.tar.gz" --project="$project" --zone="$zone" --quiet
remote_script=$(mktemp)
trap 'unlink "$remote_script"' EXIT
cat > "$remote_script" <<'REMOTE'
#!/bin/bash
set -euo pipefail
cd /opt/bitly
tar -xzf /tmp/bitly-bundle.tar.gz
if [[ ! -f .env ]]; then
  umask 077
  printf 'POSTGRES_PASSWORD=%s\nJWT_SECRET=%s\nBIND_ADDRESS=0.0.0.0\nPORT=80\n' "$(openssl rand -hex 24)" "$(openssl rand -hex 32)" > .env
fi
docker compose up -d --build --remove-orphans --wait --wait-timeout 300
curl -fsS http://127.0.0.1/health/read
curl -fsS http://127.0.0.1/health/write
REMOTE
gcloud compute scp "$remote_script" "$instance:/tmp/bitly-deploy.sh" --project="$project" --zone="$zone" --quiet
gcloud compute ssh "$instance" --project="$project" --zone="$zone" --quiet --command='sudo bash /tmp/bitly-deploy.sh'
echo "Tunnel: gcloud compute ssh $instance --project=$project --zone=$zone -- -N -L 8080:localhost:80"
echo 'Open http://localhost:8080 and register/sign in.'
