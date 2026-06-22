#!/bin/bash
# Wrapper — usa Docker Compose v2 standalone (sem bug urllib3)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOCAL_COMPOSE="$PROJECT_DIR/bin/docker-compose"

if [ -x "$LOCAL_COMPOSE" ]; then
  exec "$LOCAL_COMPOSE" "$@"
fi

if docker compose version >/dev/null 2>&1; then
  exec docker compose "$@"
fi

if command -v docker-compose >/dev/null 2>&1; then
  exec docker-compose "$@"
fi

echo "ERRO: Docker Compose não encontrado."
echo "Execute: ./scripts/fix-docker.sh"
exit 1