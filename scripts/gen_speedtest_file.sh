#!/bin/bash
# Gera arquivo estático para teste TR-069 DownloadDiagnostics
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)/examples/speedtest"
mkdir -p "$DIR"
OUT="$DIR/100mb.bin"
echo "Gerando $OUT (100 MB)..."
dd if=/dev/urandom of="$OUT" bs=1M count=100 status=progress
ls -lh "$OUT"
echo "URL TR-069: http://SEU_IP:8000/examples/speedtest/100mb.bin"