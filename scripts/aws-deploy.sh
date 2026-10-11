#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${SSH_KEY:?Set SSH_KEY to the private key matching ssh_public_key in terraform.tfvars}"
[[ -f infra/terraform.tfvars ]] || { echo 'Copy infra/terraform.tfvars.example and configure it first.'; exit 1; }
terraform -chdir=infra init
terraform -chdir=infra fmt
terraform -chdir=infra validate
terraform -chdir=infra plan -out=plan
# Terraform displays the concrete resource plan and requests approval here.
read -r -p 'Apply this plan and create billable AWS resources? Type deploy: ' answer
[[ "$answer" == deploy ]] || exit 1
terraform -chdir=infra apply plan
ip=$(terraform -chdir=infra output -raw public_ip)
ssh_opts=(-i "$SSH_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new)
ready=false
for attempt in {1..60}; do
  if ssh "${ssh_opts[@]}" "ec2-user@$ip" 'test -f /opt/bitly/bootstrap-ready'; then ready=true; break; fi
  sleep 10
done
[[ "$ready" == true ]] || { echo 'Bootstrap did not complete. Inspect /var/log/cloud-init-output.log via SSH. Resources remain; run aws-destroy.sh to remove them.'; exit 1; }
# Upload only source; never send local .env or Terraform state.
tar -czf .bundle.tar.gz app gateway requirements.txt Dockerfile compose.yaml .dockerignore
scp "${ssh_opts[@]}" .bundle.tar.gz "ec2-user@$ip:/tmp/bitly-bundle.tar.gz"
ssh "${ssh_opts[@]}" "ec2-user@$ip" 'sudo bash -s' <<'REMOTE'
set -euo pipefail
cd /opt/bitly
tar -xzf /tmp/bitly-bundle.tar.gz
if [[ ! -f .env ]]; then
  umask 077
  printf 'POSTGRES_PASSWORD=%s\nJWT_SECRET=%s\nBIND_ADDRESS=0.0.0.0\nPORT=80\n' "$(openssl rand -hex 24)" "$(openssl rand -hex 32)" > .env
fi
if ! grep -q '^JWT_SECRET=' .env; then
  printf '\nJWT_SECRET=%s\nJWT_TTL_MINUTES=30\n' "$(openssl rand -hex 32)" >> .env
fi
docker compose up -d --build --remove-orphans --wait --wait-timeout 240
for attempt in {1..30}; do
  if curl -fsS http://localhost/health; then exit 0; fi
  sleep 2
done
docker compose logs gateway read write
exit 1
REMOTE
printf '\nApp: http://%s\nUse an SSH tunnel for management (HTTP is unencrypted):\n' "$ip"
printf 'ssh -i "$SSH_KEY" -L 8080:localhost:80 ec2-user@%s\n' "$ip"
echo 'Open http://localhost:8080 and register an account or sign in.'
