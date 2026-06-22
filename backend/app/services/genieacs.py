"""Integração GenieACS — transforma device document em Inform Inspear."""

from typing import Any, Optional
from ..schemas.api import DeviceInformPayload

# Parâmetros TR-069 comuns no GenieACS (chave flat)
GENIEACS_PARAM_MAP = {
    "InternetGatewayDevice.DeviceInfo.SerialNumber": "serial_number",
    "InternetGatewayDevice.DeviceInfo.Manufacturer": "manufacturer",
    "InternetGatewayDevice.DeviceInfo.ModelName": "model",
    "InternetGatewayDevice.DeviceInfo.SoftwareVersion": "firmware",
    "InternetGatewayDevice.DeviceInfo.UpTime": "uptime_seconds",
    "InternetGatewayDevice.WANDevice.1.X_GponInterafceConfig.RXPower": "optical_rx_power",
    "InternetGatewayDevice.WANDevice.1.X_GponInterafceConfig.TXPower": "optical_tx_power",
    "InternetGatewayDevice.WANDevice.1.X_GponInterafceConfig.TransceiverTemperature": "optical_temperature",
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.ConnectionStatus": "pppoe_status",
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.Username": "pppoe_username",
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.ExternalIPAddress": "ipv4_address",
    "InternetGatewayDevice.LANDevice.1.LANEthernetInterfaceConfig.1.Status": "lan_status",
    "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.TotalAssociations": "wifi_clients_count",
    "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.SSID": "wifi_ssid",
    "InternetGatewayDevice.DeviceInfo.X_HW_CpuUsage": "cpu_usage",
    "InternetGatewayDevice.DeviceInfo.X_HW_MemoryUsage": "memory_usage",
    "InternetGatewayDevice.DeviceInfo.X_HW_CpuUsed": "cpu_usage",
    "InternetGatewayDevice.DeviceInfo.X_HW_MemUsed": "memory_usage",
}


def _wlan_band(idx: int, band_raw: Any, channel: int | None, ssid: Any) -> str:
    """Detecta 2.4G/5G — Huawei, Realtek IGD e similares."""
    if band_raw and not isinstance(band_raw, dict):
        b = str(band_raw).upper()
        if "5" in b and "2" not in b.replace("5", "", 1):
            return "5G"
        if "2" in b or "2.4" in b:
            return "2.4G"
    if channel is not None:
        if channel >= 36:
            return "5G"
        if 1 <= channel <= 14:
            return "2.4G"
    if ssid:
        s = str(ssid).lower()
        if "5g" in s or "_5g" in s or "-5g" in s:
            return "5G"
        if "2.4" in s or "2g" in s:
            return "2.4G"
    return "5G" if idx >= 5 else "2.4G"


def _unwrap(val: Any) -> Any:
    if isinstance(val, dict) and "_value" in val:
        return val["_value"]
    return val


def _get_nested(device: dict, path: str) -> Any:
    parts = path.split(".")
    cur: Any = device
    for part in parts:
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def extract_wifi_stats(device: dict) -> dict:
    """Agrega todas as WLANConfiguration (2.4G + 5G) e clientes associados."""
    wlan_root = _get_nested(device, "InternetGatewayDevice.LANDevice.1.WLANConfiguration")
    if not isinstance(wlan_root, dict):
        return {"wifi_clients_count": 0, "wifi_networks": [], "wifi_clients": [], "wifi_ssid": None}

    total = 0
    networks: list[dict] = []
    clients: list[dict] = []
    primary_ssid = None
    rssi_values: list[float] = []

    for key, cfg in wlan_root.items():
        if not key.isdigit() or not isinstance(cfg, dict):
            continue
        idx = int(key)
        ssid = _unwrap(cfg.get("SSID"))
        assoc = _unwrap(cfg.get("TotalAssociations"))
        count = int(assoc) if assoc is not None else 0
        total += count
        band_raw = _unwrap(cfg.get("X_HW_RFBand")) or _unwrap(cfg.get("X_CT-COM_RFBand"))
        channel_raw = _unwrap(cfg.get("Channel"))
        channel = _int(channel_raw)
        band = _wlan_band(idx, band_raw, channel, ssid)
        enabled = _unwrap(cfg.get("Enable"))
        beacon = _unwrap(cfg.get("BeaconType"))
        beacon_str = str(beacon) if beacon else ""
        is_open = beacon_str.lower() == "basic"
        if ssid:
            networks.append({
                "index": idx,
                "ssid": str(ssid),
                "band": str(band),
                "clients": count,
                "channel": channel,
                "enabled": str(enabled).lower() in ("1", "true") if enabled is not None else True,
                "beacon_type": beacon_str or None,
                "open": is_open,
                "security_label": "Aberta" if is_open else ("WPA" if beacon_str else "—"),
            })
            if primary_ssid is None and count > 0:
                primary_ssid = str(ssid)

        ad = cfg.get("AssociatedDevice")
        if isinstance(ad, dict):
            for ck, cv in ad.items():
                if not ck.isdigit() or not isinstance(cv, dict):
                    continue
                mac = _unwrap(cv.get("AssociatedDeviceMACAddress"))
                rssi = _unwrap(cv.get("AssociatedDeviceRssi")) or _unwrap(cv.get("X_HW_RSSI"))
                name = _unwrap(cv.get("X_HW_AssociatedDevicedescriptions"))
                ip = _unwrap(cv.get("AssociatedDeviceIPAddress"))
                if mac:
                    entry = {
                        "mac": str(mac),
                        "rssi": _float(rssi),
                        "wlan_index": idx,
                        "ssid": ssid,
                        "name": str(name) if name else None,
                        "ip": str(ip) if ip else None,
                    }
                    clients.append(entry)
                    if rssi is not None:
                        rssi_values.append(float(rssi))

    if primary_ssid is None and networks:
        primary_ssid = networks[0]["ssid"]

    # Algumas ONTs (ex. Realtek IGD V2.0.03) reportam TotalAssociations sem AssociatedDevice.*
    if total > 0 and not clients:
        for net in networks:
            n = int(net.get("clients") or 0)
            for i in range(n):
                clients.append({
                    "mac": None,
                    "rssi": None,
                    "wlan_index": net["index"],
                    "ssid": net["ssid"],
                    "name": f"Cliente {i + 1}",
                    "ip": None,
                    "detail_unavailable": True,
                })

    return {
        "wifi_clients_count": total,
        "wifi_networks": networks,
        "wifi_clients": clients,
        "wifi_ssid": primary_ssid,
        "wifi_signal_avg": sum(rssi_values) / len(rssi_values) if rssi_values else None,
    }


def _get_param(device: dict, path: str) -> Any:
    """GenieACS: chave flat ou árvore aninhada InternetGatewayDevice.*"""
    if path in device:
        return _unwrap(device[path])

    parts = path.split(".")
    cur: Any = device
    for part in parts:
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return _unwrap(cur)


def genieacs_device_to_inform(device: dict) -> DeviceInformPayload:
    """
    Converte documento de device do GenieACS NBI/webhook para DeviceInformPayload.
    device: JSON retornado por GET /devices/?query={...}
    """
    flat = {}
    for ga_path, field in GENIEACS_PARAM_MAP.items():
        val = _get_param(device, ga_path)
        if val is not None:
            flat[field] = val

    device_id = device.get("_deviceId") or {}
    serial = (
        flat.get("serial_number")
        or device_id.get("_SerialNumber")
        or device.get("_id")
        or _get_param(device, "DeviceID.SerialNumber")
        or "unknown"
    )

    manufacturer = flat.get("manufacturer") or device_id.get("_Manufacturer") or "Huawei"
    if not flat.get("model"):
        flat["model"] = device_id.get("_ProductClass")
    mfr_l = str(manufacturer).lower()
    model_l = str(flat.get("model") or "").lower()
    fw_l = str(flat.get("firmware") or "").lower()
    if "huawei" in mfr_l:
        flat["adapter"] = "huawei"
    elif "realtek" in mfr_l or model_l == "igd" or "v2.0.03" in fw_l:
        flat["adapter"] = "realtek"

    pppoe_raw = flat.get("pppoe_status")
    if pppoe_raw:
        flat["pppoe_status"] = "connected" if str(pppoe_raw).lower() in ("connected", "up") else "disconnected"

    # Online: GenieACS _lastInform (não usar hora do sync)
    from datetime import datetime, timezone, timedelta
    from ..config import settings

    inform_at = None
    is_online = False
    if device.get("_lastInform"):
        try:
            inform_at = datetime.fromisoformat(str(device["_lastInform"]).replace("Z", "+00:00"))
            is_online = (datetime.now(timezone.utc) - inform_at) < timedelta(
                minutes=settings.offline_threshold_minutes
            )
        except Exception:
            is_online = False

    mgmt_ip = flat.get("ipv4_address")
    wifi = extract_wifi_stats(device)
    flat.update(wifi)

    return DeviceInformPayload(
        serial_number=str(serial),
        manufacturer=str(manufacturer),
        model=flat.get("model"),
        firmware=flat.get("firmware"),
        adapter=flat.get("adapter"),
        is_online=is_online,
        inform_at=inform_at,
        mgmt_ip=str(mgmt_ip) if mgmt_ip else None,
        optical_rx_power=_float(flat.get("optical_rx_power")),
        optical_tx_power=_float(flat.get("optical_tx_power")),
        optical_temperature=_float(flat.get("optical_temperature")),
        uptime_seconds=_int(flat.get("uptime_seconds")),
        pppoe_status=flat.get("pppoe_status"),
        pppoe_username=flat.get("pppoe_username"),
        ipv4_address=flat.get("ipv4_address"),
        lan_status=flat.get("lan_status"),
        wifi_ssid=wifi.get("wifi_ssid") or flat.get("wifi_ssid"),
        wifi_clients_count=_int(wifi.get("wifi_clients_count")) or 0,
        wifi_signal_avg=_float(wifi.get("wifi_signal_avg")),
        cpu_usage=_float(flat.get("cpu_usage")),
        memory_usage=_float(flat.get("memory_usage")),
        parameters=flat,
    )


def _float(v) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, dict) and "_value" in v:
        v = v["_value"]
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _int(v) -> Optional[int]:
    if v is None:
        return None
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return None