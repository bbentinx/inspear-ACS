import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Integer, BigInteger, Float, Text, ForeignKey, DateTime, SmallInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class Pop(Base):
    __tablename__ = "pops"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    city: Mapped[str | None] = mapped_column(String(64))


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(256), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(32), default="noc")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_code: Mapped[str | None] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(256))
    phone: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(256))
    address: Mapped[str | None] = mapped_column(Text)
    neighborhood: Mapped[str | None] = mapped_column(String(128))
    pop_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("pops.id"))
    pppoe_login: Mapped[str | None] = mapped_column(String(128), unique=True)
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    devices: Mapped[list["Device"]] = relationship(back_populates="customer")


class Device(Base):
    __tablename__ = "devices"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    serial_number: Mapped[str] = mapped_column(String(64), unique=True)
    mac_wan: Mapped[str | None] = mapped_column(String(17))
    manufacturer: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(128))
    firmware: Mapped[str | None] = mapped_column(String(64))
    device_type: Mapped[str] = mapped_column(String(32), default="ont")
    customer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"))
    pop_id: Mapped[int | None] = mapped_column(Integer)
    olt_id: Mapped[int | None] = mapped_column(Integer)
    pon_id: Mapped[int | None] = mapped_column(Integer)
    onu_id: Mapped[int | None] = mapped_column(Integer)
    cto_id: Mapped[int | None] = mapped_column(Integer)
    concentrator_id: Mapped[int | None] = mapped_column(Integer)
    is_online: Mapped[bool] = mapped_column(Boolean, default=False)
    mgmt_ip: Mapped[str | None] = mapped_column(INET)
    last_inform_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    health_score: Mapped[int] = mapped_column(SmallInteger, default=100)
    health_status: Mapped[str] = mapped_column(String(16), default="healthy")
    adapter_type: Mapped[str] = mapped_column(String(32), default="generic")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    customer: Mapped["Customer | None"] = relationship(back_populates="devices")
    config_profile: Mapped["DeviceConfigProfile | None"] = relationship(
        back_populates="device", uselist=False
    )


class DeviceConfigProfile(Base):
    """Configuração desejada da ONT — usada para restore remoto após reset."""
    __tablename__ = "device_config_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("devices.id"), unique=True)
    serial_number: Mapped[str] = mapped_column(String(64))
    acs_url: Mapped[str | None] = mapped_column(Text)
    acs_username: Mapped[str | None] = mapped_column(String(128))
    acs_password: Mapped[str | None] = mapped_column(String(128))
    cr_username: Mapped[str | None] = mapped_column(String(128))
    cr_password: Mapped[str | None] = mapped_column(String(128))
    periodic_inform_interval: Mapped[int] = mapped_column(Integer, default=300)
    pppoe_username: Mapped[str | None] = mapped_column(String(128))
    pppoe_password: Mapped[str | None] = mapped_column(String(256))
    wan_vlan: Mapped[int | None] = mapped_column(Integer)
    wifi_24_ssid: Mapped[str | None] = mapped_column(String(64))
    wifi_24_password: Mapped[str | None] = mapped_column(String(128))
    wifi_5_ssid: Mapped[str | None] = mapped_column(String(64))
    wifi_5_password: Mapped[str | None] = mapped_column(String(128))
    auto_restore_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String(32), default="auto")
    last_captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    device: Mapped["Device"] = relationship(back_populates="config_profile")


class DeviceSnapshot(Base):
    __tablename__ = "device_snapshots"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("devices.id"))
    source: Mapped[str] = mapped_column(String(32), default="api")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    optical_rx_power: Mapped[float | None] = mapped_column(Float)
    optical_tx_power: Mapped[float | None] = mapped_column(Float)
    pppoe_status: Mapped[str | None] = mapped_column(String(32))
    ipv4_address: Mapped[str | None] = mapped_column(INET)
    ipv6_prefix: Mapped[str | None] = mapped_column(String(64))
    ipv6_status: Mapped[str | None] = mapped_column(String(32))
    wifi_clients_count: Mapped[int] = mapped_column(Integer, default=0)
    cpu_usage: Mapped[float | None] = mapped_column(Float)
    memory_usage: Mapped[float | None] = mapped_column(Float)
    reboot_count_24h: Mapped[int] = mapped_column(Integer, default=0)
    uptime_seconds: Mapped[int | None] = mapped_column(BigInteger)
    normalized: Mapped[dict] = mapped_column(JSONB, default=dict)
    raw_payload: Mapped[dict] = mapped_column(JSONB, default=dict)


class DeviceEvent(Base):
    __tablename__ = "device_events"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("devices.id"))
    event_type: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(16), default="info")
    title: Mapped[str] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Diagnosis(Base):
    __tablename__ = "diagnoses"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("devices.id"))
    snapshot_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("device_snapshots.id"))
    problem_code: Mapped[str] = mapped_column(String(64))
    problem_label: Mapped[str] = mapped_column(String(256))
    severity: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float] = mapped_column(Float)
    evidences: Mapped[list] = mapped_column(JSONB, default=list)
    counter_evidences: Mapped[list] = mapped_column(JSONB, default=list)
    recommended_action: Mapped[str] = mapped_column(Text)
    responsible_team: Mapped[str] = mapped_column(String(32))
    health_score: Mapped[int | None] = mapped_column(SmallInteger)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    device_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("devices.id"))
    diagnosis_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("diagnoses.id"))
    alert_type: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(16))
    message: Mapped[str] = mapped_column(Text)
    scope_type: Mapped[str | None] = mapped_column(String(32))
    fired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notified_telegram: Mapped[bool] = mapped_column(Boolean, default=False)