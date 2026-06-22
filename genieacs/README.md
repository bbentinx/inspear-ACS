# GenieACS + Inspear

## Subir stack completa

```bash
cd /home/noc-01/inspear
make ready    # tudo pronto: API + GenieACS + dados demo + testes
# ou
make up-full  # só containers
make setup-genieacs && make seed && make test
```

## Portas

| Serviço | Porta | Uso |
|---------|-------|-----|
| genieacs-cwmp | 7547 | ONTs Huawei apontam ACS URL aqui |
| genieacs-nbi | 7557 | API REST |
| genieacs-ui | 3001 | Interface admin GenieACS |

## Configurar ONT Huawei (EG8145V5 / X610)

Na ONT — **System Management → TR-069** (todos os campos * são obrigatórios):

| Campo | Valor |
|-------|-------|
| ACS URL | `http://IP_DO_SERVIDOR:7547` |
| ACS User Name | `inspear` |
| ACS Password | `inspear123` |
| Connection Request User Name | `inspear-cr` |
| Connection Request Password | `inspear123` |
| Enable ACS Management | ✓ |
| Enable Periodic Informing | ✓ |
| Informing Interval | `300` |

Credenciais configuradas via `make setup-genieacs` (cwmp.auth no GenieACS).

## Provision Inspear

1. Acesse GenieACS UI: http://localhost:3001
2. Admin → Provisions → criar provision `inspear`
3. Cole conteúdo de `provisions/inspear.js`
4. Admin → Presets → adicionar provision `inspear` ao preset default

A cada Inform, o script POST para:
`http://inspear-api:8000/api/v1/acs/genieacs/webhook`

Header: `X-API-Key: inspear-dev-key`

## Teste manual webhook

```bash
curl -X POST http://localhost:8000/api/v1/acs/genieacs/webhook \
  -H "Content-Type: application/json" \
  -H "X-API-Key: inspear-dev-key" \
  -d '{
    "_id": "HWTC4857553A",
    "InternetGatewayDevice.DeviceInfo.SerialNumber": "HWTC4857553A",
    "InternetGatewayDevice.DeviceInfo.Manufacturer": "Huawei",
    "InternetGatewayDevice.DeviceInfo.ModelName": "HG8245X6-10",
    "InternetGatewayDevice.WANDevice.1.X_GponInterafceConfig.RXPower": -28.5,
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.ConnectionStatus": "Connected",
    "_lastInform": "2026-06-22T12:00:00Z"
  }'
```