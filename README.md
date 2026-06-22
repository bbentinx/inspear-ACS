# Inspear ACS Inteligente

ACS inteligente para ONTs Huawei (TR-069 / GenieACS): painel web com topologia visual, diagnósticos, restore remoto pós-reset e provisionamento.

## Interface do painel

### Aba Equipamento — Topologia EG8145V5

Visão interativa da ONT: topologia de rede, portas LAN, Wi-Fi e redirecionamento de porta.

![Topologia EG8145V5 com rede Wi-Fi aberta confirmada na ONT](docs/images/equipamento-topologia-wifi-aberto.jpg)

| Área | Descrição |
|------|-----------|
| **Topologia** | Nós clicáveis — Internet, Wi-Fi, portas LAN 1–4, Celular, Servidor |
| **ONT central** | EG8145V5 com status online e links ativos (linhas verdes) |
| **Badges inferiores** | WAN, clientes Wi-Fi, regras de redirecionamento, SSID 2.4G/5G |
| **Painel Wi-Fi** | Rede aberta (`BeaconType Basic`) ou com senha — confirmação na ONT |
| **Confirmação** | Banner verde quando a alteração é aplicada com sucesso |

ONT homologada: **Huawei EG8145V5**.

---

### Aba Diagnósticos — Ações remotas e restore

Sync, connection request, reboot, firmware, speed test, ping e restore automático após reset físico.

![Diagnósticos — ações remotas ACS e restore pós-reset](docs/images/diagnosticos-ont-offline-restore.jpg)

| Área | Descrição |
|------|-----------|
| **Banner offline** | Aviso quando a ONT não informa ao ACS — métricas da última leitura |
| **Ações remotas ACS** | Sincronizar, Connection Request, Reboot e upload de firmware |
| **Restore remoto** | Perfil salvo (PPPoE, Wi-Fi, ACS) reaplicado no BOOT da ONT |
| **Configuração** | PPPoE, VLAN, Wi-Fi e credenciais ACS editáveis antes de gravar na ONT |
| **Testes** | Speed test (download/upload), ping por destino, traceroute |

Comandos enviados com ONT offline ficam na fila do GenieACS e aplicam no próximo Inform (~30s).

Documentação detalhada: [docs/equipamento.md](docs/equipamento.md) · [docs/diagnosticos.md](docs/diagnosticos.md)

---

## Instalação em servidor novo

```bash
./install.sh --ip SEU_IP --yes
```

Guia completo: **[INSTALL.md](INSTALL.md)** (sempre com GenieACS TR-069).

---

## Problema `http+docker` no docker-compose?

O `docker-compose` v1 do Ubuntu quebra com `urllib3>=2`. **Já corrigido** — o projeto baixa Docker Compose v2 automaticamente.

```bash
cd ~/inspear
make fix-docker   # baixa Compose v2 em bin/ (sem sudo)
make up           # sobe o sistema
```

## Início rápido

```bash
make up           # stack principal (postgres, api, worker, web)
make seed         # dados de teste
make test         # validação E2E
make status       # URLs e health
```

**Login painel:** http://localhost:3000 — `admin@inspear.local` / `admin123`

## Se `make up` falhar no build do web

```bash
make up-core      # sobe só postgres + redis + api + worker
make dev-web      # painel local (npm run dev na porta 3000)
```

## GenieACS (opcional)

```bash
make up-full      # inclui GenieACS TR-069 (:7547)
```

Imagens do registry oficial (`docker.genieacs.com`) podem falhar por certificado TLS — usamos `drumsergio/genieacs` do Docker Hub no profile `genieacs`.

## Comandos

| Comando | Função |
|---------|--------|
| `make fix-docker` | Corrige Docker Compose |
| `make up` | Sobe stack principal |
| `make up-core` | Backend sem container web |
| `make up-full` | + GenieACS |
| `make seed` | Importa CSV + Inform teste |
| `make test` | Teste E2E |
| `make logs` | Logs api/worker/web |
| `make down` | Para tudo |
| `make reset` | Apaga volumes e recria |

## Alternativa manual (sem Make)

```bash
./scripts/fix-docker.sh
./bin/docker-compose up -d --build
./scripts/seed_demo.sh
```