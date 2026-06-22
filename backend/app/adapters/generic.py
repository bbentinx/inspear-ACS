"""Generic TR-069 Adapter — fallback para qualquer CPE."""

from .base import BaseAdapter, NormalizedDeviceState


class GenericTR069Adapter(BaseAdapter):
    manufacturer = "generic"

    def can_handle(self, payload: dict) -> bool:
        return True  # fallback

    def normalize(self, payload: dict) -> NormalizedDeviceState:
        p = payload.get("parameters")
        if p is None or not isinstance(p, dict):
            p = payload
        dns = p.get("dns_servers", [])
        if isinstance(dns, str):
            dns = [s.strip() for s in dns.split(",") if s.strip()]

        return NormalizedDeviceState(
            serial_number=str(p.get("serial_number", p.get("SerialNumber", "unknown"))),
            manufacturer=str(p.get("manufacturer", "Unknown")),
            model=str(p.get("model", p.get("ModelName", "Unknown"))),
            firmware=p.get("firmware"),
            uptime_seconds=self._safe_int(p.get("uptime_seconds")),
            reboot_count_24h=self._safe_int(p.get("reboot_count_24h")) or 0,
            optical_rx_power=self._safe_float(p.get("optical_rx_power")),
            optical_tx_power=self._safe_float(p.get("optical_tx_power")),
            optical_temperature=self._safe_float(p.get("optical_temperature")),
            wan_status=self._map_status(p.get("wan_status")),
            pppoe_status=p.get("pppoe_status", "unknown"),
            ipv4_address=p.get("ipv4_address"),
            ipv6_prefix=p.get("ipv6_prefix"),
            ipv6_status=p.get("ipv6_status"),
            dns_servers=dns,
            dns_status=p.get("dns_status"),
            lan_status=self._map_status(p.get("lan_status")),
            wifi_clients_count=self._safe_int(p.get("wifi_clients_count")) or 0,
            wifi_signal_avg=self._safe_float(p.get("wifi_signal_avg")),
            cpu_usage=self._safe_float(p.get("cpu_usage")),
            memory_usage=self._safe_float(p.get("memory_usage")),
            is_online=p.get("is_online", True),
            recent_events=p.get("recent_events") or [],
        )