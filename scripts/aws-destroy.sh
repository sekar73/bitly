#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo 'This deletes the instance, ALL AWS link data, networking, key pair and project budget.'
terraform -chdir=infra init
terraform -chdir=infra plan -destroy -out=plan
read -r -p 'Permanently delete the resources shown? Type destroy: ' answer
[[ "$answer" == destroy ]] || exit 1
terraform -chdir=infra apply plan
echo 'Removal complete. Verify EC2 instances and volumes in us-east-1; billing reports can lag.'
