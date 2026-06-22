"""Worker — sync periódico GenieACS NBI + fila Redis."""

import asyncio
import json
import logging
from datetime import datetime, timezone

import redis
from sqlalchemy import select

from ..config import settings
from ..database import async_session
from ..models.entities import Device
from ..services.genieacs_client import genieacs_client
from ..services.genieacs import genieacs_device_to_inform
from ..services.ingest import ingest_inform

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("inspear.worker")

QUEUE_KEY = "inspear:inform:queue"


async def sync_from_genieacs() -> dict:
    """Busca todos devices no GenieACS e ingere."""
    if not settings.genieacs_sync_enabled:
        return {"skipped": True, "reason": "sync disabled"}

    if not await genieacs_client.is_available():
        log.warning("GenieACS NBI indisponível — sync ignorado")
        return {"skipped": True, "reason": "genieacs offline"}

    devices = await genieacs_client.list_devices()
    synced, errors = 0, 0
    seen_serials: set[str] = set()
    async with async_session() as db:
        for ga_doc in devices:
            try:
                inform = genieacs_device_to_inform(ga_doc)
                if inform.serial_number in ("unknown", "") or inform.serial_number.startswith("TEST"):
                    continue
                seen_serials.add(inform.serial_number)
                await ingest_inform(db, inform, force_snapshot=True)
                synced += 1
            except Exception as e:
                errors += 1
                await db.rollback()
                log.error("Sync %s: %s", ga_doc.get("_id"), e)

        # ONT sumiu do GenieACS (reset, desprovisionada) → offline imediato
        r = await db.execute(select(Device).where(Device.is_online == True))
        for d in r.scalars().all():
            if d.serial_number not in seen_serials:
                d.is_online = False
                d.health_status = "offline"
                d.health_score = min(d.health_score or 0, 15)

        await db.commit()

    log.info("Sync GenieACS: %d/%d OK, %d erros", synced, len(devices), errors)
    return {"synced": synced, "total": len(devices), "errors": errors}


async def mark_stale_offline():
    """Marca devices sem inform recente como offline."""
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.offline_threshold_minutes)
    async with async_session() as db:
        r = await db.execute(select(Device).where(Device.is_online == True))
        for d in r.scalars().all():
            if not d.last_inform_at:
                d.is_online = False
                d.health_status = "offline"
                continue
            last = d.last_inform_at
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            if last < cutoff:
                d.is_online = False
                d.health_status = "offline"
                d.health_score = min(d.health_score or 0, 15)
        await db.commit()


async def process_queue_item(data: dict):
    from ..schemas.api import DeviceInformPayload
    async with async_session() as db:
        payload = DeviceInformPayload(**data)
        await ingest_inform(db, payload)
        await db.commit()


async def main_loop():
    r = redis.from_url(settings.redis_url)
    interval = settings.genieacs_sync_interval_seconds
    log.info("Worker iniciado — sync a cada %ds", interval)

    last_sync = 0.0
    while True:
        try:
            # Fila Redis
            item = r.blpop(QUEUE_KEY, timeout=2)
            if item:
                _, raw = item
                data = json.loads(raw)
                await process_queue_item(data)
                log.info("Fila processada: %s", data.get("serial_number"))

            # Sync periódico
            now = asyncio.get_event_loop().time()
            if now - last_sync >= interval:
                await sync_from_genieacs()
                last_sync = now

            # Marca offline por timeout a cada ciclo (~60s)
            await mark_stale_offline()

        except Exception as e:
            log.exception("Erro worker: %s", e)

        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main_loop())