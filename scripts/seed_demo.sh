#!/bin/bash
set -euo pipefail
API="${API_URL:-http://localhost:8000}/api/v1"
API_KEY="${INSPEAR_API_KEY:-inspear-dev-key}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@inspear.local}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin123}"

echo "=== Login ==="
TOKEN=$(curl -s -X POST "$API/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}" | jq -r .access_token)

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
  echo "ERRO: falha no login"
  exit 1
fi
AUTH="Authorization: Bearer $TOKEN"

echo "=== Importando clientes CSV ==="
curl -s -X POST "$API/import/customers" -H "$AUTH" \
  -F "file=@examples/customers_import.csv" | jq .

echo "=== Importando equipamentos CSV ==="
curl -s -X POST "$API/import/devices" -H "$AUTH" \
  -F "file=@examples/devices_import.csv" | jq .

echo "=== Enviando Inform Huawei X610 ==="
curl -s -X POST "$API/acs/inform" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d @examples/huawei_x610_inform.json | jq .

echo "=== Concluído ==="