#!/bin/bash
# Aguarda serviço HTTP ficar pronto
URL="${1:-http://localhost:8000/health}"
MAX="${2:-60}"
i=0
while [ $i -lt $MAX ]; do
  if curl -sf "$URL" >/dev/null 2>&1; then
    echo "OK: $URL"
    exit 0
  fi
  i=$((i+1))
  sleep 2
done
echo "TIMEOUT: $URL"
exit 1