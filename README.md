# Inspear ACS Inteligente

## Instalação em servidor novo

```bash
./install.sh --ip SEU_IP --yes
```

Documentação completa: **[INSTALL.md](INSTALL.md)** (sempre com GenieACS TR-069).

Capturas de tela:
- **[docs/equipamento.md](docs/equipamento.md)** — topologia e Wi-Fi aberto na EG8145V5
- **[docs/diagnosticos.md](docs/diagnosticos.md)** — ações remotas ACS e restore pós-reset

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