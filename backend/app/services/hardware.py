"""Topologia visual EG8145V5 — leitura TR-069 e ações (Wi-Fi, redirecionamento)."""

from __future__ import annotations

from typing import Any, Optional

from .genieacs import _get_param, extract_wifi_stats
from .genieacs_client import genieacs_client
PORT_MAPPING_BASE = (
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.PortMapping"
)
LAN_BASE = "InternetGatewayDevice.LANDevice.1.LANEthernetInterfaceConfig"
WAN_PPP = (
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1"
)
GPON_RX = "InternetGatewayDevice.WANDevice.1.X_GponInterafceConfig.RXPower"

SUPPORTED_MODELS = ("EG8145V5", "EG8145X5", "HG8245")


def _scalar(val: Any) -> Any:
    if isinstance(val, dict) and "_value" in val:
        return val["_value"]
    return val


def _nested(doc: dict, path: str) -> Any:
    cur: Any = doc
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _lan_ports_from_doc(doc: dict) -> list[dict]:
    root = _nested(doc, f"InternetGatewayDevice.LANDevice.1.LANEthernetInterfaceConfig")
    if not isinstance(root, dict):
        return []
    ports = []
    for key in sorted(root.keys(), key=lambda x: int(x) if x.isdigit() else 99):
        if not key.isdigit():
            continue
        cfg = root[key]
        if not isinstance(cfg, dict):
            continue
        status = _scalar(cfg.get("Status"))
        enabled = _scalar(cfg.get("Enable"))
        speed = _scalar(cfg.get("MaxBitRate"))
        ports.append({
            "index": int(key),
            "status": str(status) if status else "Unknown",
            "enabled": str(enabled).lower() in ("1", "true", "enabled") if enabled is not None else True,
            "speed_mbps": speed,
            "connected": str(status).lower() in ("up", "connected", "enabled"),
        })
    return ports


def _port_forwards_from_doc(doc: dict) -> list[dict]:
    root = _nested(doc, PORT_MAPPING_BASE)
    if not isinstance(root, dict):
        return []
    rules = []
    for key in sorted(root.keys(), key=lambda x: int(x) if x.isdigit() else 99):
        if not key.isdigit():
            continue
        cfg = root[key]
        if not isinstance(cfg, dict):
            continue
        enabled = _scalar(cfg.get("Enable"))
        ext = _scalar(cfg.get("ExternalPort"))
        internal = _scalar(cfg.get("InternalPort"))
        client = _scalar(cfg.get("InternalClient"))
        proto = _scalar(cfg.get("Protocol"))
        desc = _scalar(cfg.get("PortMappingDescription") or cfg.get("Description"))
        if not any([ext, internal, client]):
            continue
        rules.append({
            "index": int(key),
            "enabled": str(enabled).lower() in ("1", "true") if enabled is not None else False,
            "external_port": ext,
            "internal_port": internal,
            "internal_client": client,
            "protocol": proto or "TCP",
            "description": desc or "",
        })
    return rules


async def fetch_hardware_topology(serial: str) -> dict:
    """Estado visual da ONT — WAN, Wi-Fi, LAN, redirecionamentos."""
    try:
        await genieacs_client.refresh_object(serial, PORT_MAPPING_BASE + ".")
    except Exception:
        pass
    try:
        await genieacs_client.get_parameter_values(serial, [
            f"{WAN_PPP}.ConnectionStatus",
            f"{WAN_PPP}.ExternalIPAddress",
            f"{WAN_PPP}.Username",
            f"{WAN_PPP}.X_HW_VLAN",
            GPON_RX,
            f"{LAN_BASE}.1.Status",
            f"{LAN_BASE}.2.Status",
            f"{LAN_BASE}.3.Status",
            f"{LAN_BASE}.4.Status",
            "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.BeaconType",
            "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.SSID",
            "InternetGatewayDevice.LANDevice.1.WLANConfiguration.5.BeaconType",
            "InternetGatewayDevice.LANDevice.1.WLANConfiguration.5.SSID",
        ])
    except Exception:
        pass

    doc = await genieacs_client.get_device_by_serial(serial)
    if not doc:
        return {"supported": False, "error": "ONT não encontrada no GenieACS"}

    device_id = doc.get("_deviceId") or {}
    model = device_id.get("_ProductClass") or _get_param(
        doc, "InternetGatewayDevice.DeviceInfo.ModelName"
    ) or ""
    supported = any(m in str(model).upper() for m in SUPPORTED_MODELS)

    pppoe_status = _scalar(_get_param(doc, f"{WAN_PPP}.ConnectionStatus"))
    pppoe_user = _scalar(_get_param(doc, f"{WAN_PPP}.Username"))
    ipv4 = _scalar(_get_param(doc, f"{WAN_PPP}.ExternalIPAddress"))
    vlan = _scalar(_get_param(doc, f"{WAN_PPP}.X_HW_VLAN"))
    rx = _scalar(_get_param(doc, GPON_RX))
    wifi = extract_wifi_stats(doc)

    return {
        "supported": supported,
        "model": str(model),
        "manufacturer": device_id.get("_Manufacturer") or "Huawei",
        "internet": {
            "connected": str(pppoe_status).lower() in ("connected", "up"),
            "pppoe_status": pppoe_status,
            "pppoe_username": pppoe_user,
            "ipv4": ipv4,
            "vlan": vlan,
            "optical_rx_dbm": rx,
        },
        "wifi": wifi.get("wifi_networks") or [],
        "wifi_clients": wifi.get("wifi_clients") or [],
        "wifi_clients_count": wifi.get("wifi_clients_count") or 0,
        "lan_ports": _lan_ports_from_doc(doc),
        "port_forwards": _port_forwards_from_doc(doc),
        "features": {
            "wifi_config": True,
            "port_forward": True,
            "lan_ports": 4,
            "usb": True,
        },
    }


async def add_port_forward(
    serial: str,
    external_port: int,
    internal_port: int,
    internal_client: str,
    protocol: str = "TCP",
    description: str = "",
) -> dict:
    """Cria regra de redirecionamento de porta na WAN PPPoE."""
    base = PORT_MAPPING_BASE
    try:
        add_task = await genieacs_client.add_object(serial, base)
    except Exception as e:
        return {"ok": False, "error": f"Falha ao criar slot PortMapping: {e}"}

    instance = add_task.get("instance") or add_task.get("object") or "1"
    if isinstance(instance, str) and "." in instance:
        instance = instance.rstrip(".").split(".")[-1]

    path = f"{base}.{instance}"
    params = [
        (f"{path}.Enable", True, "xsd:boolean"),
        (f"{path}.ExternalPort", external_port, "xsd:unsignedInt"),
        (f"{path}.InternalPort", internal_port, "xsd:unsignedInt"),
        (f"{path}.InternalClient", internal_client, "xsd:string"),
        (f"{path}.Protocol", protocol.upper(), "xsd:string"),
    ]
    if description:
        params.append((f"{path}.PortMappingDescription", description, "xsd:string"))

    task = await genieacs_client.set_parameter_values(serial, params)
    try:
        await genieacs_client.connection_request(serial)
    except Exception:
        pass

    return {
        "ok": True,
        "message": f"Redirecionamento {external_port} → {internal_client}:{internal_port} ({protocol})",
        "instance": instance,
        "task": task,
        "add_task": add_task,
    }


async def set_port_forward_enabled(serial: str, index: int, enabled: bool) -> dict:
    path = f"{PORT_MAPPING_BASE}.{index}.Enable"
    task = await genieacs_client.set_parameter_values(
        serial, [(path, enabled, "xsd:boolean")]
    )
    try:
        await genieacs_client.connection_request(serial)
    except Exception:
        pass
    return {
        "ok": True,
        "message": f"Regra {index} {'habilitada' if enabled else 'desabilitada'}",
        "task": task,
    }