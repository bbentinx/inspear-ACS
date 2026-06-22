#!/bin/bash
# Configura provision Inspear no GenieACS NBI (TR-069 local)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
# shellcheck disable=SC1091
[[ -f "$PROJECT_DIR/.env" ]] && set -a && source "$PROJECT_DIR/.env" && set +a
NBI="${GENIEACS_NBI_URL:-http://localhost:7557}"
# setup roda no host — NBI do container é localhost:7557
[[ "$NBI" == *genieacs:* ]] && NBI="http://localhost:7557"
PROVISION_SRC="$PROJECT_DIR/genieacs/provisions/inspear.js"
PROVISION_TMP="$(mktemp)"
ACS_USER="${GENIEACS_ACS_USER:-inspear}"
ACS_PASS="${GENIEACS_ACS_PASSWORD:-inspear123}"
CR_USER="${GENIEACS_CR_USER:-inspear-cr}"
CR_PASS="${GENIEACS_CR_PASSWORD:-inspear123}"
API_KEY="${INSPEAR_API_KEY:-inspear-dev-key}"

trap 'rm -f "$PROVISION_TMP"' EXIT
sed "s/inspear-dev-key/${API_KEY}/g" "$PROVISION_SRC" > "$PROVISION_TMP"
PROVISION_FILE="$PROVISION_TMP"

echo "=== GenieACS — setup Inspear provision ==="

if ! curl -sf "$NBI/devices/?limit=1" >/dev/null 2>&1; then
  echo "ERRO: GenieACS NBI offline em $NBI"
  echo "Rode: make up-full"
  exit 1
fi

echo "NBI online: $NBI"

# Provision script (usa hostname do container api na rede Docker)
curl -sf -X PUT "$NBI/provisions/inspear" \
  --data-binary @"$PROVISION_FILE" >/dev/null
echo "✓ Provision 'inspear' instalado"

# Preset default — executa provision em todo Inform
curl -sf -X PUT "$NBI/presets/default" \
  -H "Content-Type: application/json" \
  -d '{
    "weight": 0,
    "precondition": "true",
    "configurations": [
      {"type": "provision", "name": "inspear", "args": null}
    ]
  }' >/dev/null
echo "✓ Preset 'default' configurado"

# Autenticação CWMP (Huawei exige usuário/senha no ACS)
docker exec genieacs-mongo mongosh genieacs --quiet --eval "
db.config.updateOne(
  {_id: 'cwmp.auth'},
  {\$set: {value: 'AUTH(\"${ACS_USER}\", \"${ACS_PASS}\")'}},
  {upsert: true}
);
" >/dev/null
./scripts/compose.sh restart genieacs >/dev/null 2>&1 || true
sleep 4
echo "✓ Autenticação ACS: cwmp.auth configurado"

HOST_IP="$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'SEU_IP')"
echo ""
echo "ONT Huawei EG8145V5 — preencha TODOS os campos obrigatórios (*):"
echo "  ACS URL:                      http://${HOST_IP}:7547"
echo "  ACS User Name:                ${ACS_USER}"
echo "  ACS Password:                 ${ACS_PASS}"
echo "  Connection Request User Name: ${CR_USER}"
echo "  Connection Request Password:  ${CR_PASS}"
echo ""
echo "  Enable ACS Management:        ✓"
echo "  Enable Periodic Informing:    ✓"
echo "  Informing Interval:           300"
echo ""
echo "GenieACS UI: http://localhost:3001"
echo ""