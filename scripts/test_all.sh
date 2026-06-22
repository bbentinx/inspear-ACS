#!/bin/bash
# Teste E2E completo — Inspear ACS
set -euo pipefail

API="${API_URL:-http://localhost:8000}"
API_V1="$API/api/v1"
API_KEY="${INSPEAR_API_KEY:-inspear-dev-key}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@inspear.local}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin123}"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'
pass() { echo -e "${GREEN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }

echo "========================================"
echo " Inspear ACS — Teste E2E"
echo "========================================"

# 1. Health
echo ""
echo "--- 1. Health check ---"
HEALTH=$(curl -sf "$API/health") || fail "API offline — rode: make up"
echo "$HEALTH" | grep -q '"status":"ok"' && pass "API online" || fail "Health inválido"

# 2. Login
echo ""
echo "--- 2. Autenticação JWT ---"
LOGIN=$(curl -sf -X POST "$API_V1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}") || fail "Login falhou"
TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
[ -n "$TOKEN" ] && pass "Login OK" || fail "Token vazio"
AUTH="Authorization: Bearer $TOKEN"

# 3. Import CSV (endpoint disponível — não carrega dados fictícios automaticamente)
echo ""
echo "--- 3. Importação CSV (endpoint) ---"
IMPORT_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_V1/import/customers" -H "$AUTH" \
  -F "file=@examples/customers_import.csv")
[ "$IMPORT_CODE" = "200" ] && pass "Endpoint import/customers OK" || fail "Import clientes ($IMPORT_CODE)"

# 4. Endpoints ACS (sem injetar dados fictícios)
echo ""
echo "--- 4. Endpoints ACS ---"
INFORM_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_V1/acs/inform" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"serial_number":"SMOKE-TEST","manufacturer":"Huawei","adapter":"huawei","is_online":true}')
[ "$INFORM_CODE" = "200" ] && pass "Endpoint /acs/inform OK" || fail "Inform endpoint ($INFORM_CODE)"
./scripts/compose.sh exec -T postgres psql -U inspear -d inspear -c "DELETE FROM device_snapshots WHERE device_id IN (SELECT id FROM devices WHERE serial_number='SMOKE-TEST'); DELETE FROM diagnoses WHERE device_id IN (SELECT id FROM devices WHERE serial_number='SMOKE-TEST'); DELETE FROM devices WHERE serial_number='SMOKE-TEST';" >/dev/null 2>&1 || true

# 5. Dashboard
echo ""
echo "--- 5. Dashboard stats ---"
STATS=$(curl -sf "$API_V1/dashboard/stats" -H "$AUTH")
TOTAL=$(echo "$STATS" | python3 -c "import sys,json; print(json.load(sys.stdin)['total_devices'])")
pass "Dashboard: $TOTAL equipamentos (dados reais do ACS)"

# 6. Listar devices
echo ""
echo "--- 6. Listar equipamentos ---"
DEVICES=$(curl -sf "$API_V1/devices" -H "$AUTH")
DEVICE_COUNT=$(echo "$DEVICES" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
if [ "$DEVICE_COUNT" -gt 0 ]; then
  DEVICE_ID=$(echo "$DEVICES" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")
  SERIAL=$(echo "$DEVICES" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['serial_number'])")
  pass "Device ID: $DEVICE_ID ($SERIAL)"
else
  DEVICE_ID=""
  pass "Nenhum device ainda — normal antes da ONT informar"
fi

# 7. Ações remotas (se houver device)
echo ""
echo "--- 7. Ações remotas ACS ---"
if [ -n "$DEVICE_ID" ]; then
  SYNC=$(curl -sf -X POST "$API_V1/devices/$DEVICE_ID/actions/sync" -H "$AUTH")
  echo "$SYNC" | grep -q '"ok":true' && pass "Sync: $(echo $SYNC | python3 -c "import sys,json; print(json.load(sys.stdin)['message'])")" || fail "Sync falhou"

  REBOOT=$(curl -sf -X POST "$API_V1/devices/$DEVICE_ID/actions/reboot" -H "$AUTH")
  echo "$REBOOT" | grep -q '"ok":true' && pass "Reboot: $(echo $REBOOT | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['message']+' (simulado='+str(d.get('simulated',False))+')')")" || fail "Reboot falhou"

  CR=$(curl -sf -X POST "$API_V1/devices/$DEVICE_ID/actions/connection-request" -H "$AUTH")
  echo "$CR" | grep -q '"ok":true' && pass "Connection Request OK" || fail "CR falhou"
else
  pass "Ações remotas — aguardando ONT real"
fi

# 8. Webhook GenieACS simulado
echo ""
echo "--- 8. Webhook GenieACS ---"
WEBHOOK=$(curl -sf -X POST "$API_V1/acs/genieacs/webhook" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "_id": "HWTC4857553A",
    "InternetGatewayDevice.DeviceInfo.SerialNumber": "HWTC4857553A",
    "InternetGatewayDevice.DeviceInfo.Manufacturer": "Huawei",
    "InternetGatewayDevice.DeviceInfo.ModelName": "HG8245X6-10",
    "InternetGatewayDevice.WANDevice.1.X_GponInterafceConfig.RXPower": -28.5,
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.ConnectionStatus": "Connected",
    "_lastInform": "2026-06-22T12:00:00Z"
  }')
echo "$WEBHOOK" | grep -q '"ok":true' && pass "Webhook GenieACS OK" || fail "Webhook falhou"

# 9. GenieACS NBI (opcional)
echo ""
echo "--- 9. GenieACS NBI (opcional) ---"
if curl -sf "http://localhost:7557/devices/?limit=1" >/dev/null 2>&1; then
  pass "GenieACS NBI online em :7557"
else
  echo "  (GenieACS ainda iniciando ou offline — normal nos primeiros 60s)"
fi

# 10. Frontend
echo ""
echo "--- 10. Frontend ---"
if curl -sf "http://localhost:3000" >/dev/null 2>&1; then
  pass "Painel web online em :3000"
else
  echo "  (Web ainda buildando — aguarde e acesse http://localhost:3000)"
fi

echo ""
echo "========================================"
echo -e "${GREEN} TODOS OS TESTES PASSARAM${NC}"
echo "========================================"
echo ""
echo "Acesse:"
echo "  Painel:   http://localhost:3000"
echo "  Login:    $ADMIN_EMAIL / $ADMIN_PASSWORD"
echo "  API docs: $API/docs"
echo "  GenieACS: http://localhost:3001"
echo ""