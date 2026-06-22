"""Adapter base — normaliza parâmetros TR-069/API por fabricante."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class NormalizedDeviceState:
    """Modelo padrão interno Inspear — independente de fabricante."""

    serial_number: str
    manufacturer: str
    model: str
    firmware: Optional[str] = None
    uptime_seconds: Optional[int] = None
    last_boot_at: Optional[str] = None
    last_reboot_reason: Optional[str] = None
    reboot_count_24h: int = 0

    # Óptico (GPON)
    optical_rx_power: Optional[float] = None  # dBm
    optical_tx_power: Optional[float] = None
    optical_temperature: Optional[float] = None
    optical_voltage: Optional[float] = None
    optical_bias_current: Optional[float] = None

    # WAN / PPPoE
    wan_status: Optional[str] = None  # up, down, unknown
    pppoe_status: Optional[str] = None  # connected, disconnected, authenticating
    pppoe_username: Optional[str] = None
    ipv4_address: Optional[str] = None
    ipv6_prefix: Optional[str] = None
    ipv6_status: Optional[str] = None  # ok, no_prefix, disabled
    dns_servers: list[str] = field(default_factory=list)
    dns_status: Optional[str] = None  # ok, missing, unreachable

    # LAN
    lan_status: Optional[str] = None
    lan_speed_mbps: Optional[int] = None
    lan_errors: int = 0

    # Wi-Fi
    wifi_ssid: Optional[str] = None
    wifi_channel: Optional[int] = None
    wifi_clients_count: int = 0
    wifi_signal_avg: Optional[float] = None  # dBm RSSI médio
    wifi_networks: list[dict] = field(default_factory=list)
    wifi_clients: list[dict] = field(default_factory=list)

    # Sistema
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    mgmt_ip: Optional[str] = None
    is_online: bool = True
    last_error: Optional[str] = None

    # Eventos recentes
    recent_events: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class BaseAdapter(ABC):
    """Interface para adapters de fabricante."""

    manufacturer: str = "generic"

    @abstractmethod
    def can_handle(self, payload: dict) -> bool:
        ...

    @abstractmethod
    def normalize(self, payload: dict) -> NormalizedDeviceState:
        ...

    def _safe_float(self, val: Any) -> Optional[float]:
        if val is None or val == "":
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    def _safe_int(self, val: Any) -> Optional[int]:
        if val is None or val == "":
            return None
        try:
            return int(val)
        except (ValueError, TypeError):
            return None

    def _map_status(self, val: Any, up_values: set[str] | None = None) -> str:
        if val is None:
            return "unknown"
        s = str(val).lower()
        up = up_values or {"up", "connected", "true", "1", "enabled", "online"}
        if s in up:
            return "up"
        if s in {"down", "disconnected", "false", "0", "disabled", "offline"}:
            return "down"
        return "unknown"