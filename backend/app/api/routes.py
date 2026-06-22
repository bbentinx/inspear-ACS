from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..api.deps import get_current_user
from ..models.entities import Customer, Device, Diagnosis, Alert, DeviceSnapshot, DeviceEvent, Pop
from ..schemas.api import (
    CustomerCreate, CustomerResponse,
    DeviceCreate, DeviceResponse,
    DashboardStats, DiagnosisResponse,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.post("/customers", response_model=CustomerResponse)
async def create_customer(data: CustomerCreate, db: AsyncSession = Depends(get_db)):
    c = Customer(**data.model_dump())
    db.add(c)
    await db.flush()
    return c


@router.get("/customers", response_model=list[CustomerResponse])
async def list_customers(db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Customer).order_by(Customer.name))
    return r.scalars().all()


@router.post("/devices", response_model=DeviceResponse)
async def create_device(data: DeviceCreate, db: AsyncSession = Depends(get_db)):
    customer_id = data.customer_id
    if data.pppoe_login and not customer_id:
        r = await db.execute(select(Customer).where(Customer.pppoe_login == data.pppoe_login))
        c = r.scalar_one_or_none()
        if c:
            customer_id = c.id

    d = Device(
        serial_number=data.serial_number,
        mac_wan=data.mac_wan,
        manufacturer=data.manufacturer,
        model=data.model,
        firmware=data.firmware,
        customer_id=customer_id,
        pop_id=data.pop_id,
        olt_id=data.olt_id,
        pon_id=data.pon_id,
        onu_id=data.onu_id,
        cto_id=data.cto_id,
        concentrator_id=data.concentrator_id,
    )
    db.add(d)
    await db.flush()
    return DeviceResponse(
        id=d.id, serial_number=d.serial_number, manufacturer=d.manufacturer,
        model=d.model, firmware=d.firmware, is_online=d.is_online,
        health_score=d.health_score, health_status=d.health_status,
        last_inform_at=d.last_inform_at, pop_id=d.pop_id,
    )


@router.get("/devices", response_model=list[DeviceResponse])
async def list_devices(
    status: str | None = None,
    pop_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(Device).options(selectinload(Device.customer))
    if status == "offline":
        q = q.where(Device.is_online == False)
    elif status == "critical":
        q = q.where(Device.health_status == "critical")
    if pop_id:
        q = q.where(Device.pop_id == pop_id)
    q = q.order_by(Device.health_score.asc())
    r = await db.execute(q)
    devices = r.scalars().all()
    return [
        DeviceResponse(
            id=d.id, serial_number=d.serial_number, manufacturer=d.manufacturer,
            model=d.model, firmware=d.firmware, is_online=d.is_online,
            health_score=d.health_score, health_status=d.health_status,
            last_inform_at=d.last_inform_at, pop_id=d.pop_id,
            customer_name=d.customer.name if d.customer else None,
        )
        for d in devices
    ]


@router.get("/devices/{device_id}")
async def get_device_detail(device_id: UUID, db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        select(Device).options(selectinload(Device.customer)).where(Device.id == device_id)
    )
    d = r.scalar_one_or_none()
    if not d:
        raise HTTPException(404, "Device not found")

    snap_r = await db.execute(
        select(DeviceSnapshot).where(DeviceSnapshot.device_id == device_id)
        .order_by(DeviceSnapshot.received_at.desc()).limit(1)
    )
    snap = snap_r.scalar_one_or_none()

    diag_r = await db.execute(
        select(Diagnosis).where(Diagnosis.device_id == device_id, Diagnosis.is_active == True)
    )
    diagnoses = diag_r.scalars().all()

    ev_r = await db.execute(
        select(DeviceEvent).where(DeviceEvent.device_id == device_id)
        .order_by(DeviceEvent.occurred_at.desc()).limit(20)
    )
    events = ev_r.scalars().all()

    return {
        "device": {
            "id": str(d.id),
            "serial_number": d.serial_number,
            "manufacturer": d.manufacturer,
            "model": d.model,
            "firmware": d.firmware,
            "is_online": d.is_online,
            "health_score": d.health_score,
            "health_status": d.health_status,
            "last_inform_at": d.last_inform_at,
            "mgmt_ip": d.mgmt_ip,
            "pop_id": d.pop_id,
            "olt_id": d.olt_id,
            "pon_id": d.pon_id,
            "onu_id": d.onu_id,
            "customer": {
                "id": str(d.customer.id),
                "name": d.customer.name,
                "pppoe_login": d.customer.pppoe_login,
                "neighborhood": d.customer.neighborhood,
            } if d.customer else None,
        },
        "snapshot": snap.normalized if snap else None,
        "snapshot_at": snap.received_at if snap else None,
        "data_stale": not d.is_online,
        "diagnoses": [
            {
                "problem_code": x.problem_code,
                "problem_label": x.problem_label,
                "severity": x.severity,
                "confidence": x.confidence,
                "evidences": x.evidences,
                "counter_evidences": x.counter_evidences,
                "recommended_action": x.recommended_action,
                "responsible_team": x.responsible_team,
            }
            for x in diagnoses
        ],
        "events": [
            {"type": e.event_type, "severity": e.severity, "title": e.title,
             "description": e.description, "at": e.occurred_at}
            for e in events
        ],
    }


@router.get("/diagnoses/recent", response_model=list[DiagnosisResponse])
async def recent_diagnoses(limit: int = 50, db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        select(Diagnosis).where(Diagnosis.is_active == True)
        .order_by(Diagnosis.created_at.desc()).limit(limit)
    )
    return r.scalars().all()


@router.get("/diagnoses/list")
async def list_diagnoses(limit: int = 50, db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        select(Diagnosis, Device)
        .join(Device, Diagnosis.device_id == Device.id)
        .options(selectinload(Device.customer))
        .where(Diagnosis.is_active == True)
        .order_by(Diagnosis.created_at.desc())
        .limit(limit)
    )
    rows = r.all()
    return [
        {
            "id": d.id,
            "problem_label": d.problem_label,
            "severity": d.severity,
            "confidence": d.confidence,
            "responsible_team": d.responsible_team,
            "device_serial": dev.serial_number,
            "customer_name": dev.customer.name if dev.customer else None,
        }
        for d, dev in rows
    ]


def _aggregate_impact(devices: list[Device], pops: dict[int, str]) -> tuple[list[dict], list[dict]]:
    by_pop: dict[int, dict] = {}
    by_model: dict[str, dict] = {}

    for d in devices:
        if d.health_status not in ("critical", "degraded", "attention"):
            continue
        if d.pop_id:
            entry = by_pop.setdefault(d.pop_id, {
                "type": "pop", "name": pops.get(d.pop_id, f"POP {d.pop_id}"),
                "affected": 0, "critical": 0, "degraded": 0, "diagnosis": "",
            })
            entry["affected"] += 1
            if d.health_status == "critical":
                entry["critical"] += 1
            else:
                entry["degraded"] += 1

        model_key = f"{d.manufacturer} {d.model}".strip()
        entry = by_model.setdefault(model_key, {
            "type": "model", "name": model_key,
            "affected": 0, "critical": 0, "degraded": 0, "diagnosis": "",
        })
        entry["affected"] += 1
        if d.health_status == "critical":
            entry["critical"] += 1
        else:
            entry["degraded"] += 1

    return list(by_pop.values()), list(by_model.values())


@router.get("/timeline")
async def timeline(limit: int = 50, db: AsyncSession = Depends(get_db)):
    alert_r = await db.execute(
        select(Alert, Device)
        .outerjoin(Device, Alert.device_id == Device.id)
        .order_by(Alert.fired_at.desc())
        .limit(limit)
    )
    event_r = await db.execute(
        select(DeviceEvent, Device)
        .join(Device, DeviceEvent.device_id == Device.id)
        .order_by(DeviceEvent.occurred_at.desc())
        .limit(limit)
    )
    items = []
    for alert, dev in alert_r.all():
        items.append({
            "at": alert.fired_at.isoformat(),
            "type": "alert",
            "title": alert.message,
            "severity": alert.severity,
            "description": alert.alert_type,
            "device_serial": dev.serial_number if dev else None,
        })
    for ev, dev in event_r.all():
        items.append({
            "at": ev.occurred_at.isoformat(),
            "type": ev.event_type,
            "title": ev.title,
            "severity": ev.severity,
            "description": ev.description,
            "device_serial": dev.serial_number,
        })
    items.sort(key=lambda x: x["at"], reverse=True)
    return items[:limit]


@router.get("/dashboard/stats", response_model=DashboardStats)
async def dashboard_stats(db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count(Device.id)))).scalar() or 0
    online = (await db.execute(select(func.count(Device.id)).where(Device.is_online == True))).scalar() or 0
    critical = (await db.execute(select(func.count(Device.id)).where(Device.health_status == "critical"))).scalar() or 0
    degraded = (await db.execute(select(func.count(Device.id)).where(Device.health_status == "degraded"))).scalar() or 0
    alerts = (await db.execute(select(func.count(Alert.id)).where(Alert.resolved_at.is_(None)))).scalar() or 0

    diag_r = await db.execute(
        select(Diagnosis, Device)
        .join(Device, Diagnosis.device_id == Device.id)
        .where(Diagnosis.is_active == True)
        .order_by(Diagnosis.created_at.desc())
        .limit(10)
    )
    recent_rows = diag_r.all()

    dev_r = await db.execute(select(Device))
    all_devices = dev_r.scalars().all()
    pop_r = await db.execute(select(Pop))
    pops = {p.id: p.name for p in pop_r.scalars().all()}
    by_pop, by_model = _aggregate_impact(all_devices, pops)

    return DashboardStats(
        total_devices=total,
        online_devices=online,
        offline_devices=total - online,
        critical_devices=critical,
        degraded_devices=degraded,
        diagnoses_24h=len(recent_rows),
        alerts_open=alerts,
        by_pop=by_pop,
        by_model=by_model,
        recent_diagnoses=[
            {
                "id": d.id,
                "problem_label": d.problem_label,
                "severity": d.severity,
                "device_id": str(d.device_id),
                "device_serial": dev.serial_number,
            }
            for d, dev in recent_rows
        ],
    )