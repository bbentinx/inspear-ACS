"""ZTE Adapter — F660/F670 e similares."""

from .base import BaseAdapter, NormalizedDeviceState


class ZTEAdapter(BaseAdapter):
    manufacturer = "ZTE"

    def can_handle(self, payload: dict) -> bool:
        mfr = str(payload.get("manufacturer", "")).lower()
        model = str(payload.get("model", "")).lower()
        return "zte" in mfr or "f660" in model or "f670" in model or "f601" in model

    def normalize(self, payload: dict) -> NormalizedDeviceState:
        p = payload.get("parameters", payload)

        return NormalizedDeviceState(
            serial_number=str(p.get("serial_number", p.get("SerialNumber", "unknown"))),
            manufacturer="ZTE",
            model=str(p.get("model", p.get("ModelName", "Unknown"))),
            firmware=p.get("firmware"),
            uptime_seconds=self._safe_int(p.get("uptime_seconds")),
            reboot_count_24h=self._safe_int(p.get("reboot_count_24h")) or 0,
            optical_rx_power=self._safe_float(p.get("optical_rx_power") or p.get("RXPower")),
            optical_tx_power=self._safe_float(p.get("optical_tx_power") or p.get("TXPower")),
            optical_temperature=self._safe_float(p.get("optical_temperature")),
            wan_status=self._map_status(p.get("wan_status")),
            pppoe_status="connected" if self._map_status(p.get("pppoe_status")) == "up" else "disconnected",
            pppoe_username=p.get("pppoe_username"),
            ipv4_address=p.get("ipv4_address"),
            ipv6_prefix=p.get("ipv6_prefix"),
            ipv6_status=p.get("ipv6_status", "no_prefix" if not p.get("ipv6_prefix") else "ok"),
            dns_servers=p.get("dns_servers", []) if isinstance(p.get("dns_servers"), list) else [],
            dns_status=p.get("dns_status", "ok" if p.get("dns_servers") else "missing"),
            lan_status=self._map_status(p.get("lan_status")),
            lan_speed_mbps=self._safe_int(p.get("lan_speed_mbps")),
            wifi_clients_count=self._safe_int(p.get("wifi_clients_count")) or 0,
            wifi_signal_avg=self._safe_float(p.get("wifi_signal_avg")),
            cpu_usage=self._safe_float(p.get("cpu_usage")),
            memory_usage=self._safe_float(p.get("memory_usage")),
            mgmt_ip=p.get("mgmt_ip"),
            is_online=p.get("is_online", True),
            recent_events=p.get("recent_events", []),
        )