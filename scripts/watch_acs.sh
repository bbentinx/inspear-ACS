#!/bin/bash
# Monitora ONT chegando no GenieACS + logs CWMP
set -euo pipefail
echo "=== Monitor ACS — Ctrl+C para sair ==="
echo "GenieACS UI: http://localhost:3001"
echo "Inspear:     http://localhost:3000"
echo ""
while true; do
  COUNT=$(curl -sf "http://localhost:7557/devices/?limit=100" 2>/dev/null | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "?")
  echo "$(date '+%H:%M:%S') — devices no GenieACS: $COUNT"
  if [ "$COUNT" != "0" ] && [ "$COUNT" != "?" ]; then
    curl -sf "http://localhost:7557/devices/?limit=5" | python3 -m json.tool 2>/dev/null | head -20
    echo ""
  fi
  sleep 5
done