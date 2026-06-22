from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


# --- Customers ---
class CustomerCreate(BaseModel):
    external_code: Optional[str] = None
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    neighborhood: Optional[str] = None
    pop_id: Optional[int] = None
    pppoe_login: Optional[str] = None


class CustomerResponse(BaseModel):
    id: UUID
    name: str
    pppoe_login: Optional[str]
    neighborhood: Optional[str]
    status: str

    class Config:
        from_attributes = True


# --- Devices ---
class DeviceCreate(BaseModel):
    serial_number: str
    mac_wan: Optional[str] = None
    manufacturer: str = "Huawei"
    model: str = "HG8245X6-10"
    firmware: Optional[str] = None
    customer_id: Optional[UUID] = None
    pop_id: Optional[int] = None
    olt_id: Optional[int] = None
    pon_id: Optional[int] = None
    onu_id: Optional[int] = None
    cto_id: Optional[int] = None
    concentrator_id: Optional[int] = None
    pppoe_login: Optional[str] = None  # auto-vincula cliente


class DeviceResponse(BaseModel):
    id: UUID
    serial_number: str
    manufacturer: str
    model: str
    firmware: Optional[str]
    is_online: bool
    health_score: int
    health_status: str
    last_inform_at: Optional[datetime]
    customer_name: Optional[str] = None
    pop_id: Optional[int] = None


# --- Ingest (simula TR-069 Inform) ---
class DeviceInformPayload(BaseModel):
    """Payload API — simula Inform TR-069/CWMP até integrar ACS real."""
    serial_number: str
    manufacturer: Optional[str] = "Huawei"
    model: Optional[str] = None
    firmware: Optional[str] = None
    adapter: Optional[str] = None  # huawei, zte, fiberhome, generic
    is_online: bool = True
    inform_at: Optional[datetime] = None  # timestamp real do Inform (GenieACS _lastInform)
    mgmt_ip: Optional[str] = None
    # Parâmetros normalizados ou brutos
    parameters: Optional[dict] = None
    optical_rx_power: Optional[float] = None
    optical_tx_power: Optional[float] = None
    optical_temperature: Optional[float] = None
    uptime_seconds: Optional[int] = None
    reboot_count_24h: Optional[int] = 0
    last_reboot_reason: Optional[str] = None
    wan_status: Optional[str] = None
    pppoe_status: Optional[str] = None
    pppoe_username: Optional[str] = None
    ipv4_address: Optional[str] = None
    ipv6_prefix: Optional[str] = None
    ipv6_status: Optional[str] = None
    dns_servers: Optional[list[str]] = None
    dns_status: Optional[str] = None
    lan_status: Optional[str] = None
    lan_speed_mbps: Optional[int] = None
    wifi_ssid: Optional[str] = None
    wifi_channel: Optional[int] = None
    wifi_clients_count: Optional[int] = 0
    wifi_signal_avg: Optional[float] = None
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    recent_events: Optional[list[dict]] = None


class IngestResponse(BaseModel):
    device_id: UUID
    serial_number: str
    health_score: int
    health_status: str
    diagnoses: list[dict]
    snapshot_id: int


class DiagnosisResponse(BaseModel):
    id: int
    device_id: UUID
    problem_code: str
    problem_label: str
    severity: str
    confidence: float
    evidences: list
    recommended_action: str
    responsible_team: str
    created_at: datetime


class DashboardStats(BaseModel):
    total_devices: int
    online_devices: int
    offline_devices: int
    critical_devices: int
    degraded_devices: int
    diagnoses_24h: int
    alerts_open: int
    by_pop: list[dict]
    by_model: list[dict]
    recent_diagnoses: list[dict]