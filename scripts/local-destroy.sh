#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "${1:-}" == "--purge" ]]; then
  echo 'Removing containers AND all local link data.'
  docker compose down --volumes --remove-orphans
else
  docker compose down --remove-orphans
  echo 'Database preserved. Use --purge to delete all local link data.'
fi
