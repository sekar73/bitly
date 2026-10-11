#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
terraform -chdir=infra/gcp init
terraform -chdir=infra/gcp plan -destroy -out=plan
echo 'This permanently deletes the GCP VM, its database disk and the project networking.'
read -r -p 'Delete the resources shown? Type destroy: ' answer
[[ "$answer" == destroy ]] || exit 1
terraform -chdir=infra/gcp apply plan
echo 'The Google Cloud project, billing link, enabled APIs and console budget remain. Review Billing afterward.'
