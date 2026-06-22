# Configuração TR-069 na ONT Huawei

Guia para apontar a ONT **Huawei EG8145V5** (e modelos similares) ao GenieACS/Inspear.

## Onde configurar na ONT

**System Management → TR-069**

Todos os campos marcados com `*` são obrigatórios na Huawei. Se faltar usuário ou senha do Connection Request, a ONT não conecta corretamente ao ACS.

## Valores padrão do sistema

Substitua `SEU_IP_SERVIDOR` pelo IP que a ONT alcança na rede (WAN ou bancada).

| Campo na ONT | Valor |
|--------------|-------|
| **ACS URL** | `http://SEU_IP_SERVIDOR:7547` |
| **ACS User Name** | `inspear` |
| **ACS Password** | `inspear123` |
| **Connection Request User Name** | `inspear-cr` |
| **Connection Request Password** | `inspear123` |
| **Enable ACS Management** | ✓ |
| **Enable Periodic Informing** | ✓ |
| **Informing Interval** | `300` (produção) ou `30` (bancada/lab) |

## Portas do servidor

| Porta | Serviço |
|-------|---------|
| **7547** | GenieACS CWMP — a ONT aponta o ACS URL aqui |
| **3001** | GenieACS UI (admin) |
| **3000** | Painel Inspear |
| **8000** | API Inspear |
| **7557** | GenieACS NBI (interno Docker) |

## Variáveis no `.env`

```env
GENIEACS_CWMP_URL=http://SEU_IP_SERVIDOR:7547
GENIEACS_ACS_USER=inspear
GENIEACS_ACS_PASSWORD=inspear123
GENIEACS_CR_USER=inspear-cr
GENIEACS_CR_PASSWORD=inspear123
PUBLIC_API_BASE_URL=http://SEU_IP_SERVIDOR:8000
```

Após alterar o `.env`, recrie os containers: `docker compose up -d --force-recreate api web`

## Aplicar autenticação no GenieACS

```bash
make setup-genieacs
```

Esse script configura `cwmp.auth` no MongoDB do GenieACS com as credenciais ACS acima e imprime a tabela para colar na ONT.

## Perfil lab Fernandópolis

| Item | Valor |
|------|-------|
| WAN VLAN | `10` |
| Wi-Fi 2.4G | `Lab-2.4G` |
| Wi-Fi 5G | `Lab-5G` |

Perfil JSON: [examples/profiles/fernandopolis-eg8145v5.json](../examples/profiles/fernandopolis-eg8145v5.json)

## Após reset físico da ONT

1. Acesse a interface local em `http://192.168.100.1`
2. Reaponte **ACS URL** e credenciais conforme a tabela acima, **ou**
3. Use **Restore remoto** no painel Inspear (aba Diagnósticos) — o perfil salvo reaplica PPPoE, Wi-Fi e ACS no próximo BOOT

## Connection Request

O GenieACS usa Connection Request para forçar Inform imediato (sync, reboot, speed test). A ONT precisa alcançar a porta **7547** do servidor ACS.

## Consultar config no painel

- **Painel:** menu **ACS** → seção **Configuração TR-069 na ONT**
- **API:** `GET /api/v1/devices/tr069-config` (JWT)
- **JSON de referência:** [examples/tr069-ont-huawei-eg8145v5.json](../examples/tr069-ont-huawei-eg8145v5.json)

## Fluxo resumido

```
ONT (TR-069) ──Inform──► GenieACS :7547
                              │
                              ▼ provision inspear.js
                         POST webhook ──► Inspear API :8000
                              │
                              ▼
                         Painel :3000 (diagnóstico, ações remotas)
```