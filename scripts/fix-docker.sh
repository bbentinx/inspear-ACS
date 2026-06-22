#!/bin/bash
# Instala Docker Compose v2 standalone em bin/ (sem sudo)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BIN="$PROJECT_DIR/bin/docker-compose"
VERSION="v2.32.4"

echo "=== Inspear — fix Docker Compose ==="

if docker version >/dev/null 2>&1; then
  docker version --format 'Docker OK: {{.Client.Version}}'
else
  echo "ERRO: Docker não está acessível. Verifique se o serviço está rodando:"
  echo "  sudo systemctl start docker"
  echo "  sudo usermod -aG docker \$USER  # depois faça logout/login"
  exit 1
fi

if [ -x "$BIN" ]; then
  echo "OK: $($BIN version)"
  exit 0
fi

echo "Baixando Docker Compose $VERSION..."
mkdir -p "$PROJECT_DIR/bin"
curl -fsSL "https://github.com/docker/compose/releases/download/${VERSION}/docker-compose-linux-x86_64" -o "$BIN"
chmod +x "$BIN"

echo "OK: $($BIN version)"
echo ""
echo "Agora rode: make up"