"""Serviço de ingestão — recebe Inform (API ou futuro CWMP) e processa."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..adapters.registry import normalize_payload, get_adapter
from ..diagnosis.engine import DiagnosisEngine
from ..models.entities import Customer, Device, DeviceSnapshot, DeviceEvent, Diagnosis, Alert
from ..services.telegram import send_telegram_alert, format_alert
from ..services.provisioning import (
    capture_profile_from_state,
    apply_restore_config,
    get_profile_by_device,
    looks_like_factory_reset,
)
from ..schemas.api import DeviceInformPayload
from ..config import settings


engine_diag = DiagnosisEngine()


def _resolve_inform_time(payload: DeviceInformPayload) -> datetime:
    if payload.inform_at:
        t = payload.inform_at
        if t.tzinfo is None:
            return t.replace(tzinfo=timezone.utc)
        return t.astimezone(timezone.utc)
    return datetime.now(timezone.utc)


async def _get_aggregation_context(db: AsyncSession, device: Device) -> dict:
    """Contexto agregado para regras de PON/POP."""
    ctx = {}
    if device.pon_id:
        # Contar snapshots recentes com sinal baixo na mesma PON (simplificado MVP)
        ctx["pon_low_signal_count"] = 0  # preenchido por query futura
    if device.pop_id:
        ctx["pop_pppoe_issue_count"] = 0
    return ctx


async def ingest_inform(
    db: AsyncSession,
    payload: DeviceInformPayload,
    *,
    force_snapshot: bool = False,
) -> dict:
    raw = payload.model_dump(mode="json")
    adapter = get_adapter(raw)
    state = normalize_payload(raw)
    inform_time = _resolve_inform_time(payload)

    # Buscar ou criar device
    result = await db.execute(select(Device).where(Device.serial_number == state.serial_number))
    device = result.scalar_one_or_none()

    if not device:
        device = Device(
            id=uuid.uuid4(),
            serial_number=state.serial_number,
            manufacturer=state.manufacturer,
            model=state.model,
            firmware=state.firmware,
            adapter_type=adapter.manufacturer.lower(),
            is_online=state.is_online,
            mgmt_ip=state.mgmt_ip,
            last_inform_at=inform_time,
        )
        db.add(device)
        await db.flush()
    else:
        device.manufacturer = state.manufacturer
        device.model = state.model
        device.firmware = state.firmware
        device.is_online = state.is_online
        device.mgmt_ip = state.mgmt_ip
        device.last_inform_at = inform_time

    # Offline — por padrão não grava snapshot (evita dados velhos do webhook).
    # Pull manual do GenieACS NBI (sync) usa force_snapshot=True.
    if not state.is_online and not force_snapshot:
        device.health_status = "offline"
        device.health_score = min(device.health_score or 0, 15)
        return {
            "device_id": device.id,
            "serial_number": device.serial_number,
            "health_score": device.health_score,
            "health_status": device.health_status,
            "health_breakdown": {},
            "diagnoses": [],
            "snapshot_id": None,
            "config_restore": None,
            "skipped_stale": True,
        }

    # Auto-vincular cliente por PPPoE
    if state.pppoe_username and not device.customer_id:
        cust_result = await db.execute(
            select(Customer).where(Customer.pppoe_login == state.pppoe_username)
        )
        customer = cust_result.scalar_one_or_none()
        if customer:
            device.customer_id = customer.id

    # Snapshot
    snapshot = DeviceSnapshot(
        device_id=device.id,
        source="api",
        optical_rx_power=state.optical_rx_power,
        optical_tx_power=state.optical_tx_power,
        pppoe_status=state.pppoe_status,
        ipv4_address=state.ipv4_address,
        ipv6_prefix=state.ipv6_prefix,
        ipv6_status=state.ipv6_status,
        wifi_clients_count=state.wifi_clients_count,
        cpu_usage=state.cpu_usage,
        memory_usage=state.memory_usage,
        reboot_count_24h=state.reboot_count_24h,
        uptime_seconds=state.uptime_seconds,
        normalized=state.to_dict(),
        raw_payload=raw,
    )
    db.add(snapshot)
    await db.flush()

    # Eventos do payload
    for ev in state.recent_events or []:
        db.add(DeviceEvent(
            device_id=device.id,
            event_type=ev.get("type", "unknown"),
            severity=ev.get("severity", "info"),
            title=ev.get("title", "Evento"),
            description=ev.get("description"),
            payload=ev,
        ))

    # Diagnóstico
    ctx = await _get_aggregation_context(db, device)
    diagnoses, score, health_status, breakdown = engine_diag.analyze(state, ctx)

    # Desativar diagnósticos anteriores
    await db.execute(
        update(Diagnosis).where(Diagnosis.device_id == device.id, Diagnosis.is_active == True).values(is_active=False)
    )

    diag_results = []
    for d in diagnoses:
        diag = Diagnosis(
            device_id=device.id,
            snapshot_id=snapshot.id,
            problem_code=d.problem_code,
            problem_label=d.problem_label,
            severity=d.severity,
            confidence=d.confidence,
            evidences=d.evidences,
            counter_evidences=d.counter_evidences,
            recommended_action=d.recommended_action,
            responsible_team=d.responsible_team,
            health_score=score,
        )
        db.add(diag)
        await db.flush()
        diag_results.append({
            "id": diag.id,
            "problem_code": d.problem_code,
            "problem_label": d.problem_label,
            "severity": d.severity,
            "confidence": d.confidence,
            "evidences": d.evidences,
            "recommended_action": d.recommended_action,
            "responsible_team": d.responsible_team,
        })

        # Alertas crit/warn
        if d.severity in ("crit", "warn"):
            alert = Alert(
                device_id=device.id,
                diagnosis_id=diag.id,
                alert_type=d.problem_code,
                severity=d.severity,
                message=d.problem_label,
                scope_type="device",
            )
            db.add(alert)
            await db.flush()

            customer_name = ""
            if device.customer_id:
                cr = await db.execute(select(Customer).where(Customer.id == device.customer_id))
                c = cr.scalar_one_or_none()
                if c:
                    customer_name = c.name

            msg = format_alert(device.serial_number, d.problem_label, d.severity, d.recommended_action, customer_name)
            notified = await send_telegram_alert(msg)
            alert.notified_telegram = notified

    device.health_score = score
    device.health_status = health_status

    # Perfil de configuração — captura automática quando ONT está saudável
    restore_result = None
    if settings.auto_capture_config_profile:
        customer = None
        if device.customer_id:
            cr = await db.execute(select(Customer).where(Customer.id == device.customer_id))
            customer = cr.scalar_one_or_none()

        norm = state.to_dict()
        if state.pppoe_status == "connected" or state.wifi_networks:
            await capture_profile_from_state(db, device, norm, customer)
        elif looks_like_factory_reset(norm):
            profile = await get_profile_by_device(db, device.id)
            if profile and profile.auto_restore_enabled:
                restore_result = await apply_restore_config(db, device, profile, trigger="auto")

    return {
        "device_id": device.id,
        "serial_number": device.serial_number,
        "health_score": score,
        "health_status": health_status,
        "health_breakdown": breakdown,
        "diagnoses": diag_results,
        "snapshot_id": snapshot.id,
        "config_restore": restore_result,
    }