#!/bin/bash
# Inspear ACS — instalador completo (um comando, sempre com GenieACS)
# Documentação: INSTALL.md
# Uso: ./install.sh [--ip SEU_IP] [--yes] [--with-speedtest]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
chmod +x "$0" 2>/dev/null || true
chmod +x ./scripts/*.sh 2>/dev/null || true

# --- opções ---
SERVER_IP=""
NONINTERACTIVE=false
WITH_SPEEDTEST=false
INSTALL_DOCKER=false

usage() {
  cat <<'EOF'
Inspear ACS — instalador

Uso:
  ./install.sh [opções]

Opções:
  --ip IP              IP do servidor (auto-detecta se omitido)
  --yes, -y            Sem perguntas — gera senhas aleatórias
  --with-speedtest     Gera arquivo 100MB para teste de velocidade TR-069
  --install-docker     Instala Docker (Ubuntu/Debian) se não estiver presente
  --help, -h           Esta ajuda

Exemplos:
  ./install.sh --yes
  ./install.sh --ip 177.11.22.33 --yes
  ./install.sh --yes --with-speedtest --install-docker

Sempre inclui GenieACS TR-069. Documentação: INSTALL.md

Após instalar:
  Painel:  http://SEU_IP:3000
  API:     http://SEU_IP:8000/docs
  ACS:     http://SEU_IP:7547  (ONT Huawei TR-069)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ip) SERVER_IP="$2"; shift 2 ;;
    --yes|-y) NONINTERACTIVE=true; shift ;;
    --with-speedtest) WITH_SPEEDTEST=true; shift ;;
    --install-docker) INSTALL_DOCKER=true; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Opção desconhecida: $1"; usage; exit 1 ;;
  esac
done

install_docker() {
  if docker version >/dev/null 2>&1; then
    return 0
  fi
  if [[ "$INSTALL_DOCKER" != true ]]; then
    return 1
  fi
  if [[ "$(id -u)" -ne 0 ]]; then
    fail "Docker ausente. Rode com sudo ou use: sudo ./install.sh --install-docker ..."
  fi
  info "Instalando Docker (Ubuntu/Debian)..."
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ca-certificates curl
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc 2>/dev/null \
    || curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/${ID} ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
  systemctl enable --now docker
  ok "Docker instalado"
}

# --- cores ---
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${CYAN}>>>${NC} $*"; }
ok()    { echo -e "${GREEN}✓${NC} $*"; }
warn()  { echo -e "${YELLOW}!${NC} $*"; }
fail()  { echo -e "${RED}✗${NC} $*"; exit 1; }

rand_hex() { openssl rand -hex "${1:-16}" 2>/dev/null || head -c "$1" /dev/urandom | xxd -p | tr -d '\n'; }

echo ""
echo "=============================================="
echo " Inspear ACS — Instalação completa"
echo "=============================================="
echo ""

# --- pré-requisitos ---
info "Verificando pré-requisitos..."

command -v curl >/dev/null 2>&1 || fail "curl não encontrado — instale: sudo apt install curl"
command -v openssl >/dev/null 2>&1 || warn "openssl não encontrado — senhas usarão fallback"

if ! docker version >/dev/null 2>&1; then
  install_docker || fail "Docker não está acessível. Opções:
  1) sudo ./install.sh --install-docker --yes
  2) sudo apt install -y docker.io && sudo systemctl enable --now docker
  3) sudo usermod -aG docker \$USER   # depois logout/login"
fi
ok "Docker OK"

# Aviso firewall (UFW)
if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q "Status: active"; then
  warn "UFW ativo — libere as portas se ONTs/painel forem acessar de fora:"
  echo "     sudo ufw allow 3000/tcp 8000/tcp 7547/tcp 7557/tcp 3001/tcp"
fi

# IP do servidor
if [[ -z "$SERVER_IP" ]]; then
  SERVER_IP="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
  [[ -z "$SERVER_IP" ]] && SERVER_IP="$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}' || true)"
  [[ -z "$SERVER_IP" ]] && SERVER_IP="127.0.0.1"
fi
ok "IP do servidor: $SERVER_IP"

# Portas livres
check_port() {
  local port=$1 name=$2
  if ss -tln 2>/dev/null | grep -q ":${port} " || netstat -tln 2>/dev/null | grep -q ":${port} "; then
    warn "Porta $port ($name) já em uso — pode haver conflito"
  fi
}
check_port 3000 "Painel web"
check_port 8000 "API"
check_port 7547 "GenieACS CWMP"
check_port 7557 "GenieACS NBI"
check_port 3001 "GenieACS UI"

# --- .env ---
info "Configurando .env..."

if [[ -f .env && "$NONINTERACTIVE" != true ]]; then
  read -r -p "Arquivo .env já existe. Sobrescrever? [s/N] " ans
  [[ "${ans,,}" != "s" && "${ans,,}" != "sim" ]] && warn "Mantendo .env existente" || rm -f .env
fi

if [[ ! -f .env ]]; then
  JWT_SECRET="$(rand_hex 24)"
  PG_PASS="$(rand_hex 12)"
  API_KEY="inspear-$(rand_hex 8)"
  ADMIN_PASS="${ADMIN_PASSWORD:-admin123}"

  if [[ "$NONINTERACTIVE" != true ]]; then
    read -r -p "Senha admin painel [$ADMIN_PASS]: " inp
    [[ -n "$inp" ]] && ADMIN_PASS="$inp"
  fi

  cat > .env <<EOF
# Gerado por install.sh em $(date -Iseconds)
APP_NAME=Inspear ACS
APP_ENV=production
SECRET_KEY=$(rand_hex 16)
API_PORT=8000
WEB_PORT=3000

POSTGRES_USER=inspear
POSTGRES_PASSWORD=${PG_PASS}
POSTGRES_DB=inspear

JWT_SECRET=${JWT_SECRET}
JWT_EXPIRE_MINUTES=480
AUTH_ENABLED=true
ADMIN_EMAIL=admin@inspear.local
ADMIN_PASSWORD=${ADMIN_PASS}

INSPEAR_API_KEY=${API_KEY}

GENIEACS_NBI_URL=http://genieacs:7557
GENIEACS_CWMP_URL=http://${SERVER_IP}:7547
GENIEACS_ACS_USER=inspear
GENIEACS_ACS_PASSWORD=inspear123
GENIEACS_CR_USER=inspear-cr
GENIEACS_CR_PASSWORD=inspear123
GENIEACS_SYNC_ENABLED=true
GENIEACS_SYNC_INTERVAL_SECONDS=300
ALLOW_SIMULATED_ACTIONS=false
OFFLINE_THRESHOLD_MINUTES=15
AUTO_CAPTURE_CONFIG_PROFILE=true

PUBLIC_API_BASE_URL=http://${SERVER_IP}:8000

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
ALERTS_ENABLED=false

OPTICAL_RX_WARN_DBM=-25
OPTICAL_RX_CRIT_DBM=-27
REBOOT_WARN_24H=3
REBOOT_CRIT_24H=6
WIFI_CLIENTS_WARN=15
WIFI_CLIENTS_CRIT=25
CPU_WARN_PCT=80
MEMORY_WARN_PCT=85

SPEED_TEST_SERVER_NAME=core Lab Fer
SPEED_TEST_SERVER_CITY=Fernandópolis
SPEED_TEST_SERVER_HOST=${SERVER_IP}:8000
SPEED_TEST_DOWNLOAD_URL=http://${SERVER_IP}:8000/examples/speedtest/100mb.bin
SPEED_TEST_UPLOAD_URL=http://speedtest.tele2.net/upload.php
EOF
  ok ".env criado"
else
  # Atualiza IPs no .env existente
  sed -i "s|^GENIEACS_CWMP_URL=.*|GENIEACS_CWMP_URL=http://${SERVER_IP}:7547|" .env 2>/dev/null || true
  sed -i "s|^PUBLIC_API_BASE_URL=.*|PUBLIC_API_BASE_URL=http://${SERVER_IP}:8000|" .env 2>/dev/null || true
  sed -i "s|^SPEED_TEST_SERVER_HOST=.*|SPEED_TEST_SERVER_HOST=${SERVER_IP}:8000|" .env 2>/dev/null || true
  sed -i "s|^SPEED_TEST_DOWNLOAD_URL=.*|SPEED_TEST_DOWNLOAD_URL=http://${SERVER_IP}:8000/examples/speedtest/100mb.bin|" .env 2>/dev/null || true
  API_KEY="$(grep '^INSPEAR_API_KEY=' .env | cut -d= -f2-)"
  ADMIN_PASS="$(grep '^ADMIN_PASSWORD=' .env | cut -d= -f2-)"
  ok ".env atualizado (IPs)"
fi

# shellcheck disable=SC1091
source .env 2>/dev/null || true
API_KEY="${INSPEAR_API_KEY:-inspear-dev-key}"
ADMIN_PASS="${ADMIN_PASSWORD:-admin123}"

# --- Docker Compose ---
info "Preparando Docker Compose..."
./scripts/fix-docker.sh

info "Subindo containers + GenieACS (build pode levar alguns minutos)..."
if ! ./scripts/compose.sh --profile genieacs up -d --build 2>&1; then
  warn "Build completo falhou — tentando core + GenieACS sem rebuild web..."
  ./scripts/compose.sh up -d --build postgres redis api worker
  ./scripts/compose.sh --profile genieacs up -d --no-build genieacs-mongo genieacs
  if ! curl -sf http://localhost:3000 >/dev/null 2>&1; then
    warn "Painel web offline — rode em dev: cd web && npm run dev"
  fi
fi

# --- aguardar serviços ---
info "Aguardando API..."
./scripts/wait_for.sh "http://localhost:8000/health" 120

info "Aguardando GenieACS..."
./scripts/wait_for.sh "http://localhost:7557/devices/?limit=1" 120

# --- migração extra (DB já existente) ---
if ./scripts/compose.sh exec -T postgres psql -U inspear -d inspear -c '\dt device_config_profiles' 2>/dev/null | grep -q device_config_profiles; then
  ok "Tabela device_config_profiles OK"
else
  info "Aplicando migração config profiles..."
  ./scripts/compose.sh exec -T postgres psql -U inspear -d inspear < sql/002_config_profiles.sql 2>/dev/null && ok "Migração 002 aplicada" || warn "Migração 002 — verifique manualmente"
fi

# --- GenieACS provision ---
info "Configurando GenieACS (provision + ACS auth)..."
export GENIEACS_NBI_URL="http://localhost:7557"
export INSPEAR_API_KEY="$API_KEY"
./scripts/setup_genieacs.sh

# --- speedtest file ---
if [[ "$WITH_SPEEDTEST" == true ]]; then
  info "Gerando arquivo speedtest (100MB)..."
  chmod +x ./scripts/gen_speedtest_file.sh
  ./scripts/gen_speedtest_file.sh || warn "Speedtest file — rode depois: make speedtest-file"
else
  mkdir -p examples/speedtest
  if [[ ! -f examples/speedtest/100mb.bin ]]; then
    info "Criando speedtest mínimo (1MB) — use --with-speedtest para 100MB"
    dd if=/dev/urandom of=examples/speedtest/100mb.bin bs=1M count=1 status=none 2>/dev/null || true
  fi
fi

# --- perfil cidade Fernandópolis ---
mkdir -p examples/profiles/generated
ok "Perfil cidade: examples/profiles/fernandopolis-eg8145v5.json"

# --- teste rápido ---
info "Teste de saúde..."
HTTP_CODE="$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health)"
[[ "$HTTP_CODE" == "200" ]] && ok "API health OK" || warn "API retornou $HTTP_CODE"

# --- salvar credenciais ---
CREDS_FILE="${SCRIPT_DIR}/CREDENCIAIS.txt"
{
  echo "Inspear ACS — credenciais ($(date -Iseconds))"
  echo "IP servidor: ${SERVER_IP}"
  echo ""
  echo "Painel: http://${SERVER_IP}:3000"
  echo "  Email: admin@inspear.local"
  echo "  Senha: ${ADMIN_PASS}"
  echo ""
  echo "API: http://${SERVER_IP}:8000/docs"
  echo "  API Key: ${API_KEY}"
  echo ""
  echo "GenieACS TR-069: http://${SERVER_IP}:7547"
  echo "  ACS User: inspear / inspear123"
  echo "  CR User:  inspear-cr / inspear123"
  echo "  UI:       http://${SERVER_IP}:3001"
} > "$CREDS_FILE"
chmod 600 "$CREDS_FILE" 2>/dev/null || true

# --- resumo ---
echo ""
echo "=============================================="
echo -e " ${GREEN}INSTALAÇÃO CONCLUÍDA${NC}"
echo "=============================================="
echo ""
echo -e " ${CYAN}Painel Inspear${NC}"
echo "   URL:    http://${SERVER_IP}:3000"
echo "   Login:  admin@inspear.local"
echo "   Senha:  ${ADMIN_PASS}"
echo ""
echo -e " ${CYAN}API${NC}"
echo "   Docs:   http://${SERVER_IP}:8000/docs"
echo "   Health: http://${SERVER_IP}:8000/health"
echo "   API Key: ${API_KEY}"
echo ""
echo -e " ${CYAN}GenieACS TR-069${NC}"
echo "   UI:     http://${SERVER_IP}:3001"
echo "   ACS URL (ONT Huawei): http://${SERVER_IP}:7547"
echo "   ACS User:     inspear"
echo "   ACS Password: inspear123"
echo "   CR User:      inspear-cr"
echo "   CR Password:  inspear123"
echo ""
echo -e " ${CYAN}ONT — configure TR-069${NC}"
echo "   ACS URL:                      http://${SERVER_IP}:7547"
echo "   Enable ACS Management:        ✓"
echo "   Enable Periodic Informing:    ✓"
echo "   Informing Interval:           300"
echo ""
echo -e " ${CYAN}Comandos úteis${NC}"
echo "   Status:   make status"
echo "   Logs:     make logs"
echo "   Parar:    make down"
echo "   Reiniciar: make up-full"
echo ""
echo " Credenciais: ${CREDS_FILE} e ${SCRIPT_DIR}/.env"
echo "=============================================="
echo ""