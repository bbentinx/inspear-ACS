#!/bin/bash
# Prepara ambiente local completo — Inspear ACS + GenieACS TR-069
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

API="${API_URL:-http://localhost:8000}"
HOST_IP="$(hostname -I 2>/dev/null | awk '{print $1}' || echo '127.0.0.1')"

echo "=============================================="
echo " Inspear ACS — Preparar teste local TR-069"
echo "=============================================="

# 1. Docker Compose v2
./scripts/fix-docker.sh

# 2. Stack completa (API + GenieACS CWMP :7547)
echo ""
echo ">>> Subindo stack completa..."
if ./scripts/compose.sh --profile genieacs up -d --build 2>/dev/null; then
  echo "Build completo OK"
else
  echo "Build web falhou (Docker Hub) — subindo core + GenieACS..."
  ./scripts/compose.sh up -d --build postgres redis api worker 2>/dev/null || \
    ./scripts/compose.sh up -d --no-build postgres redis api worker
  ./scripts/compose.sh --profile genieacs up -d --no-build genieacs-mongo genieacs
  if ! curl -sf http://localhost:3000 >/dev/null 2>&1; then
    echo "Painel web: rode 'make dev-web' em outro terminal"
  fi
fi

# 3. Aguardar serviços
echo ""
echo ">>> Aguardando API..."
./scripts/wait_for.sh "$API/health" 90

echo ">>> Aguardando GenieACS NBI..."
./scripts/wait_for.sh "http://localhost:7557/devices/?limit=1" 120

# 4. Provision GenieACS
echo ""
./scripts/setup_genieacs.sh

# 5. Teste E2E (sem dados fictícios — só valida serviços)
echo ""
./scripts/test_all.sh

echo ""
echo "=============================================="
echo " PRONTO PARA TESTAR"
echo "=============================================="
echo ""
echo "Painel Inspear:  http://localhost:3000"
echo "  Login: admin@inspear.local / admin123"
echo ""
echo "API + docs:      http://localhost:8000/docs"
echo "GenieACS UI:     http://localhost:3001"
echo ""
echo "TR-069 (ONT real):"
echo "  ACS URL → http://${HOST_IP}:7547"
echo ""
echo "Simular Inform (sem ONT):"
echo "  curl -X POST $API/api/v1/acs/inform \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -H 'X-API-Key: inspear-dev-key' \\"
echo "    -d @examples/huawei_x610_inform.json"
echo ""
echo "Webhook GenieACS:"
echo "  curl -X POST $API/api/v1/acs/genieacs/webhook \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -H 'X-API-Key: inspear-dev-key' \\"
echo "    -d @examples/genieacs_webhook_sample.json"
echo ""