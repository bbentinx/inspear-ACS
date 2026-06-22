# Aba Equipamento — Topologia EG8145V5

Visão interativa da ONT Huawei EG8145V5 no painel Inspear: topologia de rede, portas LAN, Wi-Fi e redirecionamento de porta.

![Topologia EG8145V5 com rede Wi-Fi aberta confirmada na ONT](images/equipamento-topologia-wifi-aberto.jpg)

## O que a tela mostra

| Área | Descrição |
|------|-----------|
| **Topologia** | Nós clicáveis — Internet, Wi-Fi, portas LAN 1–4, Celular, Servidor |
| **ONT central** | EG8145V5 com status online e links ativos (linhas verdes) |
| **Badges inferiores** | WAN, clientes Wi-Fi, regras de redirecionamento, SSID 2.4G/5G |
| **Painel Wi-Fi** | Configuração de rede aberta (`BeaconType Basic`) ou com senha |
| **Confirmação** | Banner verde quando a ONT aplica a alteração com sucesso |

## Exemplo nesta captura

- **Dispositivo:** Huawei EG8145V5
- **Wi-Fi 2.4G / 5G:** rede aberta (`BeaconType Basic`)
- **Status:** ONT online

## Homologação

ONTs homologadas:

| Modelo | Firmware | Fabricante |
|--------|----------|------------|
| **EG8145V5** | V5R019C00S100 | Huawei |
| **IGD** | V2.0.03-190815 | Realtek |

A Realtek IGD usa os mesmos índices TR-069 (`WLANConfiguration.1` e `.5`, `WANPPPConnection.1`). A banda Wi-Fi é detectada pelo canal/SSID, não só pelo índice.

Ver também: [Diagnósticos e restore remoto](diagnosticos.md).