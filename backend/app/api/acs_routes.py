from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..api.deps import verify_api_key
from ..schemas.api import DeviceInformPayload, IngestResponse
from ..services.ingest import ingest_inform
from ..services.genieacs import genieacs_device_to_inform
from ..services.provisioning import (
    get_profile_by_serial,
    build_provision_payload,
    apply_restore_config,
)
from ..services.vendor_config import build_vendor_xml
from ..models.entities import Device
from sqlalchemy import select

router = APIRouter(prefix="/acs", tags=["acs"])


@router.post("/inform", response_model=IngestResponse)
async def acs_inform(
    payload: DeviceInformPayload,
    db: AsyncSession = Depends(get_db),
    _key=Depends(verify_api_key),
):
    """Ingestão direta — simula Inform TR-069 ou script manual."""
    result = await ingest_inform(db, payload)
    return IngestResponse(**result)


@router.post("/genieacs/webhook")
async def genieacs_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _key=Depends(verify_api_key),
):
    """
    Webhook chamado pelo provision script do GenieACS a cada Inform.
    Body: documento completo do device (JSON do GenieACS NBI).
    """
    device = await request.json()
    inform = genieacs_device_to_inform(device)
    result = await ingest_inform(db, inform)
    return {"ok": True, **result}


@router.get("/vendor-file/{serial}.xml")
async def get_vendor_config_file(serial: str, db: AsyncSession = Depends(get_db)):
    """
    Vendor Configuration File para Download TR-069 na ONT.
    Público (ONT baixa via HTTP) — serial funciona como identificador.
    """
    clean = serial.replace(".xml", "")
    profile = await get_profile_by_serial(db, clean)
    if not profile:
        raise HTTPException(404, "Perfil não encontrado")
    xml = build_vendor_xml(profile)
    return Response(content=xml, media_type="application/xml")


@router.get("/provision/{serial}")
async def get_provision_config(
    serial: str,
    db: AsyncSession = Depends(get_db),
    _key=Depends(verify_api_key),
):
    """
    Retorna parâmetros TR-069 para restore — chamado pelo provision GenieACS no BOOT.
    """
    profile = await get_profile_by_serial(db, serial)
    if not profile or not profile.auto_restore_enabled:
        raise HTTPException(404, "Perfil não encontrado ou auto-restore desabilitado")
    payload = build_provision_payload(profile)
    if not payload["parameters"]:
        raise HTTPException(404, "Perfil sem parâmetros para aplicar")
    return payload


@router.post("/provision/{serial}/apply")
async def apply_provision_on_boot(
    serial: str,
    db: AsyncSession = Depends(get_db),
    _key=Depends(verify_api_key),
):
    """Aplica restore via TR-069 quando ONT faz BOOT (chamado pelo provision)."""
    r = await db.execute(select(Device).where(Device.serial_number == serial))
    device = r.scalar_one_or_none()
    if not device:
        raise HTTPException(404, "Equipamento não cadastrado no Inspear")
    result = await apply_restore_config(db, device, trigger="boot")
    await db.commit()
    return result


@router.post("/genieacs/sync/{device_id}")
async def genieacs_sync_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    _key=Depends(verify_api_key),
):
    """
    Sincroniza um device buscando do GenieACS NBI.
    Requer GENIEACS_NBI_URL configurado.
    """
    import httpx
    from ..config import settings
    url = f"{settings.genieacs_nbi_url}/devices/?query={{\"_id\":\"{device_id}\"}}"
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url)
        r.raise_for_status()
        devices = r.json()
    if not devices:
        return {"ok": False, "error": "Device não encontrado no GenieACS"}
    inform = genieacs_device_to_inform(devices[0])
    result = await ingest_inform(db, inform)
    return {"ok": True, **result}