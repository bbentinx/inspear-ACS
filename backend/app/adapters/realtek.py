"""Realtek Adapter — ONT IGD (ex.: V2.0.03-190815) TR-069."""

from .base import BaseAdapter, NormalizedDeviceState

# Mesma árvore TR-069 padrão IGD; índices WLAN 1 e 5 como na Huawei.
REALTEK_PATHS = {
    "serial": "InternetGatewayDevice.DeviceInfo.SerialNumber",
    "model": "InternetGatewayDevice.DeviceInfo.ModelName",
    "firmware": "InternetGatewayDevice.DeviceInfo.SoftwareVersion",
    "uptime": "InternetGatewayDevice.DeviceInfo.UpTime",
    "pppoe_status": "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.ConnectionStatus",
    "pppoe_user": "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.Username",
    "external_ip": "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.ExternalIPAddress",
    "lan_status": "InternetGatewayDevice.LANDevice.1.LANEthernetInterfaceConfig.1.Status",
    "wifi_clients": "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.TotalAssociations",
    "wifi_ssid": "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.SSID",
    "wifi_channel": "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.Channel",
}


class RealtekAdapter(BaseAdapter):
    manufacturer = "Realtek"

    def can_handle(self, payload: dict) -> bool:
        mfr = str(payload.get("manufacturer", payload.get("Manufacturer", ""))).lower()
        model = str(payload.get("model", payload.get("ModelName", ""))).lower()
        firmware = str(payload.get("firmware", payload.get("SoftwareVersion", ""))).lower()
        return (
            "realtek" in mfr
            or model == "igd"
            or "v2.0.03" in firmware
            or payload.get("adapter") == "realtek"
        )

    def normalize(self, payload: dict) -> NormalizedDeviceState:
        base = {k: v for k, v in payload.items() if k != "parameters"}
        params = payload.get("parameters")
        if isinstance(params, dict):
            p = {**base, **params}
        else:
            p = base
        if isinstance(p, dict) and "InternetGatewayDevice" in p:
            p = self._flatten_tr069(p)

        serial = p.get("serial_number") or p.get("SerialNumber") or p.get(REALTEK_PATHS["serial"], "unknown")
        model = p.get("model") or p.get("ModelName") or p.get(REALTEK_PATHS["model"], "IGD")
        firmware = p.get("firmware") or p.get("SoftwareVersion") or p.get(REALTEK_PATHS["firmware"])

        pppoe_raw = p.get("pppoe_status") or p.get(REALTEK_PATHS["pppoe_status"])
        pppoe = "connected" if self._map_status(pppoe_raw) == "up" else "disconnected"

        return NormalizedDeviceState(
            serial_number=str(serial),
            manufacturer="Realtek",
            model=str(model),
            firmware=str(firmware) if firmware else None,
            uptime_seconds=self._safe_int(p.get("uptime_seconds") or p.get("UpTime") or p.get(REALTEK_PATHS["uptime"])),
            last_boot_at=p.get("last_boot_at"),
            last_reboot_reason=p.get("last_reboot_reason"),
            reboot_count_24h=self._safe_int(p.get("reboot_count_24h")) or 0,
            optical_rx_power=self._safe_float(p.get("optical_rx_power")),
            optical_tx_power=self._safe_float(p.get("optical_tx_power")),
            optical_temperature=self._safe_float(p.get("optical_temperature")),
            wan_status=self._map_status(p.get("wan_status", pppoe_raw)),
            pppoe_status=pppoe,
            pppoe_username=p.get("pppoe_username") or p.get(REALTEK_PATHS["pppoe_user"]),
            ipv4_address=p.get("ipv4_address") or p.get("ExternalIPAddress") or p.get(REALTEK_PATHS["external_ip"]),
            ipv6_prefix=p.get("ipv6_prefix"),
            ipv6_status=p.get("ipv6_status", "no_prefix"),
            dns_servers=p.get("dns_servers") or [],
            dns_status=p.get("dns_status"),
            lan_status=self._map_status(p.get("lan_status") or p.get(REALTEK_PATHS["lan_status"])),
            wifi_ssid=p.get("wifi_ssid") or p.get(REALTEK_PATHS["wifi_ssid"]),
            wifi_channel=self._safe_int(p.get("wifi_channel") or p.get(REALTEK_PATHS["wifi_channel"])),
            wifi_clients_count=self._safe_int(p.get("wifi_clients_count") or p.get(REALTEK_PATHS["wifi_clients"])) or 0,
            wifi_signal_avg=self._safe_float(p.get("wifi_signal_avg")),
            wifi_networks=p.get("wifi_networks") or [],
            wifi_clients=p.get("wifi_clients") or [],
            cpu_usage=self._safe_float(p.get("cpu_usage")),
            memory_usage=self._safe_float(p.get("memory_usage")),
            mgmt_ip=p.get("mgmt_ip"),
            is_online=p.get("is_online", True),
            last_error=p.get("last_error"),
            recent_events=p.get("recent_events") or [],
        )

    def _flatten_tr069(self, tree: dict, prefix: str = "") -> dict:
        result = {}
        for key, val in tree.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(val, dict):
                if "_value" in val:
                    result[path] = val["_value"]
                else:
                    result.update(self._flatten_tr069(val, path))
            else:
                result[path] = val
        return result