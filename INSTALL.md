# Instalação — Inspear ACS

Instalador completo em um comando. **Sempre inclui GenieACS** (TR-069).

## Início rápido

```bash
cd inspear
chmod +x install.sh
./install.sh --ip SEU_IP_SERVIDOR --yes
```

Servidor Ubuntu/Debian **sem Docker**:

```bash
sudo ./install.sh --install-docker --ip SEU_IP_SERVIDOR --yes
```

Atalho pelo Makefile:

```bash
make install
```

## O que o script faz

1. Verifica Docker (instala com `--install-docker` se necessário)
2. Detecta o IP do servidor (ou usa `--ip`)
3. Gera `.env` com senhas aleatórias
4. Sobe **API + painel + GenieACS TR-069**
5. Aplica migrações do banco (`device_config_profiles`)
6. Configura provision GenieACS (restore remoto pós-reset)
7. Cria arquivo de speedtest mínimo (ou 100MB com `--with-speedtest`)
8. Salva credenciais em `CREDENCIAIS.txt`

## URLs após instalar

| Serviço | URL |
|---------|-----|
| Painel Inspear | `http://SEU_IP:3000` |
| API docs | `http://SEU_IP:8000/docs` |
| ACS TR-069 (ONT) | `http://SEU_IP:7547` |
| GenieACS UI | `http://SEU_IP:3001` |

**Login painel:** `admin@inspear.local` — senha exibida no final da instalação (também em `CREDENCIAIS.txt` e `.env`).

## Opções do instalador

```bash
./install.sh [opções]
```

| Opção | Descrição |
|-------|-----------|
| `--ip IP` | IP do servidor (auto-detecta se omitido) |
| `--yes`, `-y` | Sem perguntas — gera senhas aleatórias |
| `--with-speedtest` | Gera arquivo 100MB para teste de velocidade TR-069 |
| `--install-docker` | Instala Docker (Ubuntu/Debian) se não estiver presente |
| `--help`, `-h` | Ajuda |

### Exemplos

```bash
./install.sh --yes
./install.sh --ip 177.11.22.33 --yes
./install.sh --yes --with-speedtest --install-docker
```

## Firewall

Se usar UFW, libere as portas:

```bash
sudo ufw allow 3000/tcp 8000/tcp 7547/tcp 7557/tcp 3001/tcp
```

| Porta | Serviço |
|-------|---------|
| 3000 | Painel Inspear |
| 8000 | API |
| 7547 | GenieACS CWMP (ONT Huawei TR-069) |
| 7557 | GenieACS NBI (interno) |
| 3001 | GenieACS UI |

## Configurar ONT Huawei (TR-069)

Na ONT, preencha:

| Campo | Valor |
|-------|-------|
| ACS URL | `http://SEU_IP:7547` |
| ACS User Name | `inspear` |
| ACS Password | `inspear123` |
| Connection Request User Name | `inspear-cr` |
| Connection Request Password | `inspear123` |
| Enable ACS Management | ✓ |
| Enable Periodic Informing | ✓ |
| Informing Interval | `300` |

## Comandos úteis após instalar

```bash
make status      # containers + health
make logs        # logs api/worker/web
make logs-all    # logs + GenieACS
make down        # parar tudo
make up-full     # reiniciar stack completa
```

## Arquivos gerados

| Arquivo | Conteúdo |
|---------|----------|
| `.env` | Variáveis de ambiente e senhas |
| `CREDENCIAIS.txt` | Resumo de login e URLs (chmod 600) |

## Pré-requisitos

- Linux (Ubuntu/Debian recomendado)
- Docker acessível (ou `--install-docker` com sudo)
- `curl` instalado
- Portas 3000, 8000, 7547, 7557 e 3001 livres

## Copiar para outro servidor

```bash
# No servidor de origem
tar czf inspear.tar.gz inspear/

# No servidor novo
scp inspear.tar.gz usuario@servidor:/opt/
ssh usuario@servidor
cd /opt && tar xzf inspear.tar.gz && cd inspear
./install.sh --ip IP_DO_SERVIDOR --yes
```

Ou via Git:

```bash
git clone <seu-repositorio> inspear
cd inspear
./install.sh --ip SEU_IP --yes
```