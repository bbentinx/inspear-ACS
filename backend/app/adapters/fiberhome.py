"""FiberHome Adapter."""

from .base import BaseAdapter, NormalizedDeviceState


class FiberHomeAdapter(BaseAdapter):
    manufacturer = "FiberHome"

    def can_handle(self, payload: dict) -> bool:
        mfr = str(payload.get("manufacturer", "")).lower()
        return "fiberhome" in mfr or "fiber home" in mfr or "an5506" in str(payload.get("model", "")).lower()

    def normalize(self, payload: dict) -> NormalizedDeviceState:
        p = payload.get("parameters", payload)
        return NormalizedDeviceState(
            serial_number=str(p.get("serial_number", "unknown")),
            manufacturer="FiberHome",
            model=str(p.get("model", "Unknown")),
            firmware=p.get("firmware"),
            uptime_seconds=self._safe_int(p.get("uptime_seconds")),
            reboot_count_24h=self._safe_int(p.get("reboot_count_24h")) or 0,
            optical_rx_power=self._safe_float(p.get("optical_rx_power")),
            optical_tx_power=self._safe_float(p.get("optical_tx_power")),
            wan_status=self._map_status(p.get("wan_status")),
            pppoe_status="connected" if self._map_status(p.get("pppoe_status")) == "up" else "disconnected",
            ipv4_address=p.get("ipv4_address"),
            ipv6_prefix=p.get("ipv6_prefix"),
            ipv6_status=p.get("ipv6_status", "no_prefix"),
            dns_servers=p.get("dns_servers", []),
            wifi_clients_count=self._safe_int(p.get("wifi_clients_count")) or 0,
            is_online=p.get("is_online", True),
        )