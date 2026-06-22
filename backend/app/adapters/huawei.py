"""Huawei Adapter — HG8245X6 / X610 e família TR-069 Huawei."""

from .base import BaseAdapter, NormalizedDeviceState

# Mapeamento TR-069 Huawei GPON (parâmetros comuns)
HUAWEI_PATHS = {
    "serial": "InternetGatewayDevice.DeviceInfo.SerialNumber",
    "model": "InternetGatewayDevice.DeviceInfo.ModelName",
    "firmware": "InternetGatewayDevice.DeviceInfo.SoftwareVersion",
    "uptime": "InternetGatewayDevice.DeviceInfo.UpTime",
    "rx_power": "InternetGatewayDevice.WANDevice.1.X_GponInterafceConfig.RXPower",
    "tx_power": "InternetGatewayDevice.WANDevice.1.X_GponInterafceConfig.TXPower",
    "temperature": "InternetGatewayDevice.WANDevice.1.X_GponInterafceConfig.TransceiverTemperature",
    "voltage": "InternetGatewayDevice.WANDevice.1.X_GponInterafceConfig.SupplyVoltage",
    "bias": "InternetGatewayDevice.WANDevice.1.X_GponInterafceConfig.BiasCurrent",
    "pppoe_status": "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.ConnectionStatus",
    "pppoe_user": "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.Username",
    "external_ip": "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.ExternalIPAddress",
    "lan_status": "InternetGatewayDevice.LANDevice.1.LANEthernetInterfaceConfig.1.Status",
    "lan_speed": "InternetGatewayDevice.LANDevice.1.LANEthernetInterfaceConfig.1.MaxBitRate",
    "wifi_clients": "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.TotalAssociations",
    "wifi_ssid": "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.SSID",
    "wifi_channel": "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.Channel",
    "cpu": "InternetGatewayDevice.DeviceInfo.X_HW_CpuUsage",
    "memory": "InternetGatewayDevice.DeviceInfo.X_HW_MemoryUsage",
    "cpu_used": "InternetGatewayDevice.DeviceInfo.X_HW_CpuUsed",
    "mem_used": "InternetGatewayDevice.DeviceInfo.X_HW_MemUsed",
}


class HuaweiAdapter(BaseAdapter):
    manufacturer = "Huawei"

    def can_handle(self, payload: dict) -> bool:
        mfr = str(payload.get("manufacturer", payload.get("Manufacturer", ""))).lower()
        model = str(payload.get("model", payload.get("ModelName", ""))).lower()
        return (
            "huawei" in mfr
            or "hg8245" in model
            or "eg8145" in model
            or "x610" in model
            or payload.get("adapter") == "huawei"
        )

    def normalize(self, payload: dict) -> NormalizedDeviceState:
        # Suporta payload API simulado ou Inform TR-069 (dict flat ou nested)
        base = {k: v for k, v in payload.items() if k != "parameters"}
        params = payload.get("parameters")
        if isinstance(params, dict):
            p = {**base, **params}
        else:
            p = base
        if isinstance(p, dict) and "InternetGatewayDevice" in p:
            p = self._flatten_tr069(p)

        serial = p.get("serial_number") or p.get("SerialNumber") or p.get(HUAWEI_PATHS["serial"], "unknown")
        model = p.get("model") or p.get("ModelName") or p.get(HUAWEI_PATHS["model"], "Unknown")
        firmware = p.get("firmware") or p.get("SoftwareVersion") or p.get(HUAWEI_PATHS["firmware"])

        rx = self._safe_float(p.get("optical_rx_power") or p.get("rx_power") or p.get(HUAWEI_PATHS["rx_power"]))
        tx = self._safe_float(p.get("optical_tx_power") or p.get("tx_power") or p.get(HUAWEI_PATHS["tx_power"]))

        pppoe_raw = p.get("pppoe_status") or p.get(HUAWEI_PATHS["pppoe_status"])
        pppoe = "connected" if self._map_status(pppoe_raw) == "up" else "disconnected"

        ipv6_prefix = p.get("ipv6_prefix") or p.get("IPv6Prefix")
        ipv6_status = "ok" if ipv6_prefix else p.get("ipv6_status", "no_prefix")

        dns_servers = p.get("dns_servers") or []
        if isinstance(dns_servers, str):
            dns_servers = [s.strip() for s in dns_servers.split(",") if s.strip()]

        return NormalizedDeviceState(
            serial_number=str(serial),
            manufacturer="Huawei",
            model=str(model),
            firmware=str(firmware) if firmware else None,
            uptime_seconds=self._safe_int(p.get("uptime_seconds") or p.get("UpTime") or p.get(HUAWEI_PATHS["uptime"])),
            last_boot_at=p.get("last_boot_at"),
            last_reboot_reason=p.get("last_reboot_reason") or p.get("RebootReason"),
            reboot_count_24h=self._safe_int(p.get("reboot_count_24h")) or 0,
            optical_rx_power=rx,
            optical_tx_power=tx,
            optical_temperature=self._safe_float(p.get("optical_temperature") or p.get(HUAWEI_PATHS["temperature"])),
            optical_voltage=self._safe_float(p.get("optical_voltage") or p.get(HUAWEI_PATHS["voltage"])),
            optical_bias_current=self._safe_float(p.get("optical_bias_current") or p.get(HUAWEI_PATHS["bias"])),
            wan_status=self._map_status(p.get("wan_status", pppoe_raw)),
            pppoe_status=pppoe,
            pppoe_username=p.get("pppoe_username") or p.get(HUAWEI_PATHS["pppoe_user"]),
            ipv4_address=p.get("ipv4_address") or p.get("ExternalIPAddress") or p.get(HUAWEI_PATHS["external_ip"]),
            ipv6_prefix=ipv6_prefix,
            ipv6_status=ipv6_status,
            dns_servers=dns_servers,
            dns_status=p.get("dns_status") or ("ok" if dns_servers else "missing"),
            lan_status=self._map_status(p.get("lan_status") or p.get(HUAWEI_PATHS["lan_status"])),
            lan_speed_mbps=self._safe_int(p.get("lan_speed_mbps") or p.get(HUAWEI_PATHS["lan_speed"])),
            lan_errors=self._safe_int(p.get("lan_errors")) or 0,
            wifi_ssid=p.get("wifi_ssid") or p.get(HUAWEI_PATHS["wifi_ssid"]),
            wifi_channel=self._safe_int(p.get("wifi_channel") or p.get(HUAWEI_PATHS["wifi_channel"])),
            wifi_clients_count=self._safe_int(p.get("wifi_clients_count") or p.get(HUAWEI_PATHS["wifi_clients"])) or 0,
            wifi_signal_avg=self._safe_float(p.get("wifi_signal_avg")),
            wifi_networks=p.get("wifi_networks") or [],
            wifi_clients=p.get("wifi_clients") or [],
            cpu_usage=self._safe_float(
                p.get("cpu_usage") or p.get(HUAWEI_PATHS["cpu"]) or p.get(HUAWEI_PATHS["cpu_used"])
            ),
            memory_usage=self._safe_float(
                p.get("memory_usage") or p.get(HUAWEI_PATHS["memory"]) or p.get(HUAWEI_PATHS["mem_used"])
            ),
            mgmt_ip=p.get("mgmt_ip") or p.get("ManagementIP"),
            is_online=p.get("is_online", True),
            last_error=p.get("last_error"),
            recent_events=p.get("recent_events") or [],
        )

    def _flatten_tr069(self, tree: dict, prefix: str = "") -> dict:
        """Achata árvore TR-069 em dict path → value."""
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