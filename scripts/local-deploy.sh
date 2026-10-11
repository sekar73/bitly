#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -f .env ]]; then
  umask 077
  printf 'POSTGRES_PASSWORD=%s\nJWT_SECRET=%s\nBIND_ADDRESS=127.0.0.1\nPORT=8000\n' "$(openssl rand -hex 24)" "$(openssl rand -hex 32)" > .env
fi
if ! grep -q '^JWT_SECRET=' .env; then
  printf '\nJWT_SECRET=%s\nJWT_TTL_MINUTES=30\n' "$(openssl rand -hex 32)" >> .env
fi
port=$(python3 -c "from pathlib import Path; import os; print(os.environ.get('PORT') or dict(l.split('=',1) for l in Path('.env').read_text().splitlines() if '=' in l).get('PORT','8000'))")
docker compose up -d --build --remove-orphans --wait --wait-timeout 180
for attempt in {1..30}; do
  if curl -fsS "http://localhost:$port/health"; then
    printf '\nOpen http://localhost:%s. Register an account or sign in.\n' "$port"
    exit 0
  fi
  sleep 2
done
docker compose logs gateway read write
exit 1
