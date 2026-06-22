"""Ações remotas ACS — reboot, connection request, firmware."""

from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..api.deps import get_current_user
from ..models.entities import Device, DeviceEvent, User
from ..services.genieacs_client import genieacs_client, GenieACSDeviceNotFound
from ..services.genieacs import genieacs_device_to_inform
from ..services.ingest import ingest_inform
from ..services.tr069_actions import (
    SOCIAL_PING_HOSTS,
    refresh_wifi_stats,
    update_wifi,
    start_ping_test,
    start_speed_test,
    start_upload_test,
    start_traceroute,
    read_diagnostic_results,
)
from ..services.wan_counters import read_wan_counters, sample_wan_throughput
from ..services.speed_test import speed_test_config
from ..services.hardware import (
    fetch_hardware_topology,
    add_port_forward,
    set_port_forward_enabled,
)
from ..services.provisioning import (
    get_profile_by_device,
    capture_profile_from_state,
    apply_restore_config,
    apply_city_profile_to_device,
    list_city_profiles,
    load_city_profile,
    profile_to_dict,
    save_isp_default_on_device,
)
from ..models.entities import Customer, DeviceSnapshot
from ..config import settings

router = APIRouter(prefix="/devices", tags=["remote-actions"])


def _genieacs_device_missing(exc: Exception) -> bool:
    if isinstance(exc, GenieACSDeviceNotFound):
        return True
    msg = str(exc).lower()
    return "404" in msg or "not found" in msg


class ActionResponse(BaseModel):
    ok: bool
    action: str
    device_serial: str
    message: str
    genieacs_task: dict | None = None
    simulated: bool = False


class FirmwareRequest(BaseModel):
    firmware_url: HttpUrl
    file_name: str = "firmware.bin"


class WifiConfigRequest(BaseModel):
    wlan_index: int = Field(1, description="1=2.4GHz, 5=5GHz na EG8145V5")
    ssid: Optional[str] = None
    password: Optional[str] = None
    open_network: bool = Field(False, description="Rede aberta — sem senha")


class PingTestRequest(BaseModel):
    host: Optional[str] = None
    preset: Optional[str] = Field(None, description="instagram, facebook, whatsapp, tiktok, youtube")
    count: int = 4


class SpeedTestRequest(BaseModel):
    download_url: str | None = None


class UploadTestRequest(BaseModel):
    upload_url: str | None = None
    file_size: int = 10485760


class TracerouteRequest(BaseModel):
    host: Optional[str] = None
    preset: Optional[str] = None
    max_hops: int = 8


class PortForwardRequest(BaseModel):
    external_port: int = Field(..., ge=1, le=65535)
    internal_port: int = Field(..., ge=1, le=65535)
    internal_client: str = Field(..., description="IP LAN do dispositivo destino")
    protocol: str = Field("TCP", description="TCP, UDP ou TCP/UDP")
    description: str = ""


class PortForwardToggleRequest(BaseModel):
    index: int = Field(..., ge=1)
    enabled: bool = True


class ConfigProfileUpdate(BaseModel):
    acs_url: Optional[str] = None
    acs_username: Optional[str] = None
    acs_password: Optional[str] = None
    cr_username: Optional[str] = None
    cr_password: Optional[str] = None
    periodic_inform_interval: Optional[int] = None
    pppoe_username: Optional[str] = None
    pppoe_password: Optional[str] = None
    wan_vlan: Optional[int] = None
    wifi_24_ssid: Optional[str] = None
    wifi_24_password: Optional[str] = None
    wifi_5_ssid: Optional[str] = None
    wifi_5_password: Optional[str] = None
    auto_restore_enabled: Optional[bool] = None


async def _get_device(db: AsyncSession, device_id: UUID) -> Device:
    r = await db.execute(select(Device).where(Device.id == device_id))
    d = r.scalar_one_or_none()
    if not d:
        raise HTTPException(404, "Equipamento não encontrado")
    return d


def _json_safe(value):
    """Converte UUID/datetime para tipos serializáveis em JSONB."""
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


async def _log_action(
    db: AsyncSession,
    device: Device,
    action: str,
    user: User,
    result: dict,
    simulated: bool = False,
):
    db.add(DeviceEvent(
        device_id=device.id,
        event_type=f"remote_{action}",
        severity="info",
        title=f"Ação remota: {action}",
        description=f"Executado por {user.name}" + (" (simulado)" if simulated else ""),
        payload=_json_safe({"action": action, "result": result, "user": user.email}),
    ))


async def _simulated_action(
    db: AsyncSession,
    device: Device,
    action: str,
    user: User,
    message: str,
) -> ActionResponse:
    await _log_action(db, device, action, user, {"simulated": True}, simulated=True)
    return ActionResponse(
        ok=True,
        action=action,
        device_serial=device.serial_number,
        message=message,
        simulated=True,
    )


@router.post("/{device_id}/actions/connection-request", response_model=ActionResponse)
async def connection_request(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    device = await _get_device(db, device_id)
    ga_id = device.serial_number

    if await genieacs_client.is_available():
        try:
            task = await genieacs_client.connection_request(ga_id)
            await _log_action(db, device, "connection_request", user, task)
            return ActionResponse(
                ok=True, action="connection_request", device_serial=device.serial_number,
                message="Connection Request enviado — ONT deve informar em breve", genieacs_task=task,
            )
        except Exception as e:
            if settings.allow_simulated_actions and _genieacs_device_missing(e):
                return await _simulated_action(
                    db, device, "connection_request", user,
                    "Simulado — ONT ainda não registrada no GenieACS.",
                )
            err = str(e)
            if "401" in err:
                raise HTTPException(
                    502,
                    "Connection Request rejeitado (401) — senha CR da ONT não confere. "
                    "Use 'Restaurar agora' para reaplicar inspear-cr / inspear123.",
                )
            raise HTTPException(502, f"GenieACS erro: {e}")

    if settings.allow_simulated_actions:
        return await _simulated_action(
            db, device, "connection_request", user,
            "Simulado — GenieACS offline. Em produção, ONT receberia CR.",
        )
    raise HTTPException(503, "GenieACS indisponível")


@router.post("/{device_id}/actions/reboot", response_model=ActionResponse)
async def reboot_device(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    device = await _get_device(db, device_id)
    ga_id = device.serial_number

    if await genieacs_client.is_available():
        try:
            task = await genieacs_client.reboot(ga_id)
            await _log_action(db, device, "reboot", user, task)
            return ActionResponse(
                ok=True, action="reboot", device_serial=device.serial_number,
                message="Reboot enviado via TR-069", genieacs_task=task,
            )
        except Exception as e:
            if settings.allow_simulated_actions and _genieacs_device_missing(e):
                return await _simulated_action(
                    db, device, "reboot", user,
                    "Simulado — ONT ainda não registrada no GenieACS.",
                )
            raise HTTPException(502, f"GenieACS erro: {e}")

    if settings.allow_simulated_actions:
        return await _simulated_action(
            db, device, "reboot", user,
            "Simulado — GenieACS offline",
        )
    raise HTTPException(503, "GenieACS indisponível")


@router.post("/{device_id}/actions/firmware-upgrade", response_model=ActionResponse)
async def firmware_upgrade(
    device_id: UUID,
    body: FirmwareRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    device = await _get_device(db, device_id)
    ga_id = device.serial_number
    url = str(body.firmware_url)

    if await genieacs_client.is_available():
        try:
            task = await genieacs_client.download_firmware(ga_id, url, body.file_name)
            await _log_action(db, device, "firmware_upgrade", user, {"url": url, **task})
            return ActionResponse(
                ok=True, action="firmware_upgrade", device_serial=device.serial_number,
                message=f"Download firmware iniciado: {url}", genieacs_task=task,
            )
        except Exception as e:
            if settings.allow_simulated_actions and _genieacs_device_missing(e):
                return await _simulated_action(
                    db, device, "firmware_upgrade", user,
                    f"Simulado — ONT não registrada. URL: {url}",
                )
            raise HTTPException(502, f"GenieACS erro: {e}")

    if settings.allow_simulated_actions:
        return await _simulated_action(
            db, device, "firmware_upgrade", user,
            f"Simulado — firmware URL: {url}",
        )
    raise HTTPException(503, "GenieACS indisponível")


@router.post("/{device_id}/actions/sync", response_model=ActionResponse)
async def sync_device(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Sincroniza parâmetros do GenieACS NBI e roda diagnóstico."""
    device = await _get_device(db, device_id)
    ga_id = await genieacs_client.resolve_device_id(device.serial_number)
    if ga_id:
        try:
            await refresh_wifi_stats(device.serial_number)
            await genieacs_client.get_parameter_values(ga_id, [
                "InternetGatewayDevice.DeviceInfo.X_HW_CpuUsed",
                "InternetGatewayDevice.DeviceInfo.X_HW_MemUsed",
                "InternetGatewayDevice.WANDevice.1.X_GponInterafceConfig.RXPower",
                "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.ConnectionStatus",
            ])
        except Exception:
            pass

    ga_doc = await genieacs_client.get_device_by_serial(device.serial_number)

    if not ga_doc:
        device.is_online = False
        device.health_status = "offline"
        device.health_score = min(device.health_score or 0, 15)
        await _log_action(db, device, "sync", user, {"offline": True, "reason": "not_in_genieacs"})
        await db.commit()
        raise HTTPException(
            404,
            "ONT não encontrada no GenieACS — marcada como offline. "
            "Dados exibidos são da última leitura.",
        )

    inform = genieacs_device_to_inform(ga_doc)
    result = await ingest_inform(db, inform)
    await _log_action(db, device, "sync", user, result)
    return ActionResponse(
        ok=True, action="sync", device_serial=device.serial_number,
        message=f"Sincronizado — health score: {result['health_score']}",
        genieacs_task={"health_score": result["health_score"]},
    )


@router.post("/actions/sync-all")
async def sync_all_devices(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Sincroniza todos os devices do GenieACS (manual)."""
    if not await genieacs_client.is_available():
        raise HTTPException(503, "GenieACS indisponível")

    devices = await genieacs_client.list_devices()
    synced, errors = 0, []
    for ga_doc in devices:
        try:
            inform = genieacs_device_to_inform(ga_doc)
            await ingest_inform(db, inform)
            synced += 1
        except Exception as e:
            errors.append(f"{ga_doc.get('_id')}: {e}")

    return {"ok": True, "synced": synced, "total": len(devices), "errors": errors}


@router.get("/provisioning/cities")
async def get_city_provisioning_profiles(
    user: User = Depends(get_current_user),
):
    return {"ok": True, "cities": list_city_profiles()}


@router.get("/provisioning/cities/{city_code}")
async def get_city_provisioning_profile(
    city_code: str,
    user: User = Depends(get_current_user),
):
    template = load_city_profile(city_code)
    if not template:
        raise HTTPException(404, f"Perfil de cidade não encontrado: {city_code}")
    return {"ok": True, "profile": template}


@router.get("/{device_id}/config-profile")
async def get_config_profile(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    device = await _get_device(db, device_id)
    profile = await get_profile_by_device(db, device.id)
    if not profile:
        return {"ok": False, "profile": None, "message": "Perfil não cadastrado — capture ou preencha manualmente"}
    return {"ok": True, "profile": profile_to_dict(profile, include_secrets=True)}


@router.put("/{device_id}/config-profile")
async def update_config_profile(
    device_id: UUID,
    body: ConfigProfileUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from datetime import datetime, timezone
    from ..models.entities import DeviceConfigProfile

    device = await _get_device(db, device_id)
    profile = await get_profile_by_device(db, device.id)
    if not profile:
        from ..services.provisioning import _acs_defaults
        profile = DeviceConfigProfile(
            device_id=device.id,
            serial_number=device.serial_number,
            source="manual",
            **_acs_defaults(),
        )
        db.add(profile)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    profile.source = "manual"
    profile.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True, "profile": profile_to_dict(profile, include_secrets=True)}


@router.post("/{device_id}/actions/apply-city-profile", response_model=ActionResponse)
async def apply_city_profile(
    device_id: UUID,
    city_code: str = "fernandopolis",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Aplica padrão da cidade (Fernandópolis: VLAN 10, ACS, Wi-Fi Lab)."""
    device = await _get_device(db, device_id)
    customer = None
    if device.customer_id:
        cr = await db.execute(select(Customer).where(Customer.id == device.customer_id))
        customer = cr.scalar_one_or_none()
    try:
        profile = await apply_city_profile_to_device(db, device, city_code, customer)
    except ValueError as e:
        raise HTTPException(404, str(e))
    await _log_action(db, device, "apply_city_profile", user, {
        "city": city_code, "wan_vlan": profile.wan_vlan,
    })
    await db.commit()
    return ActionResponse(
        ok=True,
        action="apply_city_profile",
        device_serial=device.serial_number,
        message=f"Padrão {city_code} aplicado — VLAN {profile.wan_vlan}, Wi-Fi {profile.wifi_24_ssid}",
    )


@router.post("/{device_id}/actions/capture-config", response_model=ActionResponse)
async def capture_config_profile(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Salva configuração atual da ONT como perfil desejado."""
    device = await _get_device(db, device_id)
    snap_r = await db.execute(
        select(DeviceSnapshot).where(DeviceSnapshot.device_id == device_id)
        .order_by(DeviceSnapshot.received_at.desc()).limit(1)
    )
    snap = snap_r.scalar_one_or_none()
    customer = None
    if device.customer_id:
        cr = await db.execute(select(Customer).where(Customer.id == device.customer_id))
        customer = cr.scalar_one_or_none()

    norm = dict(snap.normalized) if snap and snap.normalized else {}
    if customer and not norm.get("pppoe_username"):
        norm["pppoe_username"] = customer.pppoe_login

    profile = await capture_profile_from_state(db, device, norm, customer)
    await _log_action(db, device, "capture_config", user, {"profile_id": str(profile.id)})
    await db.commit()
    return ActionResponse(
        ok=True,
        action="capture_config",
        device_serial=device.serial_number,
        message="Perfil salvo — PPPoE e Wi-Fi prontos para restore remoto",
    )


@router.post("/{device_id}/actions/save-isp-default", response_model=ActionResponse)
async def save_isp_default(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Grava padrão ISP na ONT (PPPoE VLAN 10 + ACS + Wi-Fi) como config de fábrica.
    Requer senha PPPoE e senhas Wi-Fi no perfil.
    """
    device = await _get_device(db, device_id)
    result = await save_isp_default_on_device(db, device)
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "Falha ao gravar padrão"))
    await _log_action(db, device, "save_isp_default", user, {
        "vendor_url": result.get("vendor_url"),
        "steps": result.get("steps"),
    })
    await db.commit()
    return ActionResponse(
        ok=True,
        action="save_isp_default",
        device_serial=device.serial_number,
        message=result.get("message", "Padrão gravado na ONT"),
        genieacs_task={
            "steps": result.get("steps"),
            "backup_verified": result.get("backup_verified"),
            "backup_point": result.get("backup_point"),
            "test_hint": result.get("test_hint"),
            "reset_note": result.get("reset_note"),
        },
    )


@router.post("/{device_id}/actions/restore-config", response_model=ActionResponse)
async def restore_config_profile(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Reaplica configuração salva na ONT via TR-069 (sem visita técnica)."""
    device = await _get_device(db, device_id)
    result = await apply_restore_config(db, device, trigger="manual")
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "Falha no restore"))
    await _log_action(db, device, "restore_config", user, result)
    await db.commit()
    return ActionResponse(
        ok=True,
        action="restore_config",
        device_serial=device.serial_number,
        message=result.get("message", "Configuração restaurada"),
        genieacs_task=result.get("task"),
    )


@router.get("/{device_id}/hardware")
async def get_device_hardware(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Topologia visual EG8145V5 — WAN, Wi-Fi, LAN, redirecionamentos."""
    device = await _get_device(db, device_id)
    try:
        topo = await fetch_hardware_topology(device.serial_number)
    except GenieACSDeviceNotFound:
        raise HTTPException(404, "ONT não encontrada no GenieACS")
    except Exception as e:
        raise HTTPException(502, f"Erro ao ler hardware: {e}")
    topo["device_online"] = device.is_online
    topo["serial"] = device.serial_number
    return topo


@router.post("/{device_id}/actions/port-forward", response_model=ActionResponse)
async def create_port_forward(
    device_id: UUID,
    body: PortForwardRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    device = await _get_device(db, device_id)
    try:
        result = await add_port_forward(
            device.serial_number,
            body.external_port,
            body.internal_port,
            body.internal_client,
            body.protocol,
            body.description,
        )
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "Falha"))
        await _log_action(db, device, "port_forward", user, result)
        await db.commit()
        return ActionResponse(
            ok=True,
            action="port_forward",
            device_serial=device.serial_number,
            message=result["message"],
            genieacs_task=result.get("task"),
        )
    except GenieACSDeviceNotFound:
        raise HTTPException(404, "ONT não encontrada no GenieACS")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Erro redirecionamento: {e}")


@router.post("/{device_id}/actions/port-forward/toggle", response_model=ActionResponse)
async def toggle_port_forward(
    device_id: UUID,
    body: PortForwardToggleRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    device = await _get_device(db, device_id)
    try:
        result = await set_port_forward_enabled(
            device.serial_number, body.index, body.enabled
        )
        await _log_action(db, device, "port_forward_toggle", user, result)
        await db.commit()
        return ActionResponse(
            ok=True,
            action="port_forward_toggle",
            device_serial=device.serial_number,
            message=result["message"],
            genieacs_task=result.get("task"),
        )
    except GenieACSDeviceNotFound:
        raise HTTPException(404, "ONT não encontrada no GenieACS")
    except Exception as e:
        raise HTTPException(502, f"Erro: {e}")


@router.post("/{device_id}/actions/wifi", response_model=ActionResponse)
async def configure_wifi(
    device_id: UUID,
    body: WifiConfigRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    device = await _get_device(db, device_id)
    try:
        result = await update_wifi(
            device.serial_number,
            wlan_index=body.wlan_index,
            ssid=body.ssid,
            password=body.password,
            open_network=body.open_network,
        )
        await _log_action(db, device, "wifi_config", user, result)
        return ActionResponse(
            ok=True, action="wifi_config", device_serial=device.serial_number,
            message=result["message"], genieacs_task=result.get("task"),
        )
    except GenieACSDeviceNotFound:
        raise HTTPException(404, "ONT não encontrada no GenieACS")
    except Exception as e:
        raise HTTPException(502, f"Erro Wi-Fi: {e}")


@router.post("/{device_id}/actions/ping-test", response_model=ActionResponse)
async def ping_test(
    device_id: UUID,
    body: PingTestRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    device = await _get_device(db, device_id)
    host = body.host
    if body.preset:
        host = SOCIAL_PING_HOSTS.get(body.preset, body.preset)
    if not host:
        raise HTTPException(400, "Informe host ou preset (instagram, facebook, etc.)")
    try:
        result = await start_ping_test(device.serial_number, host, body.count)
        await _log_action(db, device, "ping_test", user, result)
        return ActionResponse(
            ok=True, action="ping_test", device_serial=device.serial_number,
            message=result["message"], genieacs_task=result.get("task"),
        )
    except GenieACSDeviceNotFound:
        raise HTTPException(404, "ONT não encontrada no GenieACS")
    except Exception as e:
        raise HTTPException(502, f"Erro ping: {e}")


@router.get("/speed-test/config")
async def get_speed_test_config(user: User = Depends(get_current_user)):
    return speed_test_config()


@router.post("/{device_id}/actions/speed-test", response_model=ActionResponse)
async def speed_test(
    device_id: UUID,
    body: SpeedTestRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    device = await _get_device(db, device_id)
    try:
        result = await start_speed_test(device.serial_number, body.download_url)
        await _log_action(db, device, "speed_test", user, result)
        return ActionResponse(
            ok=True, action="speed_test", device_serial=device.serial_number,
            message=result["message"], genieacs_task=result.get("task"),
        )
    except GenieACSDeviceNotFound:
        raise HTTPException(404, "ONT não encontrada no GenieACS")
    except Exception as e:
        raise HTTPException(502, f"Erro speed test: {e}")


@router.post("/{device_id}/actions/upload-test", response_model=ActionResponse)
async def upload_test(
    device_id: UUID,
    body: UploadTestRequest = UploadTestRequest(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    device = await _get_device(db, device_id)
    try:
        result = await start_upload_test(
            device.serial_number, body.upload_url, body.file_size
        )
        await _log_action(db, device, "upload_test", user, result)
        return ActionResponse(
            ok=True, action="upload_test", device_serial=device.serial_number,
            message=result["message"], genieacs_task=result.get("task"),
        )
    except GenieACSDeviceNotFound:
        raise HTTPException(404, "ONT não encontrada no GenieACS")
    except Exception as e:
        raise HTTPException(502, f"Erro upload: {e}")


@router.post("/{device_id}/actions/traceroute", response_model=ActionResponse)
async def traceroute_test(
    device_id: UUID,
    body: TracerouteRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    device = await _get_device(db, device_id)
    host = body.host
    if body.preset:
        host = SOCIAL_PING_HOSTS.get(body.preset, body.preset)
    if not host:
        raise HTTPException(400, "Informe host ou preset")
    try:
        result = await start_traceroute(device.serial_number, host, body.max_hops)
        await _log_action(db, device, "traceroute", user, result)
        return ActionResponse(
            ok=True, action="traceroute", device_serial=device.serial_number,
            message=result["message"], genieacs_task=result.get("task"),
        )
    except GenieACSDeviceNotFound:
        raise HTTPException(404, "ONT não encontrada no GenieACS")
    except Exception as e:
        raise HTTPException(502, f"Erro traceroute: {e}")


@router.get("/{device_id}/diagnostics/{kind}")
async def get_diagnostics(
    device_id: UUID,
    kind: str,
    direction: str = "download",
    interval: float = 3.0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if kind not in ("ping", "speed", "upload", "traceroute", "wifi", "wan-counters", "wan-bandwidth"):
        raise HTTPException(400, "kind inválido")
    device = await _get_device(db, device_id)
    try:
        if kind == "wan-counters":
            return await read_wan_counters(device.serial_number)
        if kind == "wan-bandwidth":
            if direction not in ("download", "upload"):
                raise HTTPException(400, "direction deve ser download ou upload")
            return await sample_wan_throughput(
                device.serial_number,
                direction=direction,  # type: ignore[arg-type]
                interval_s=max(interval, 1.0),
            )
        return await read_diagnostic_results(device.serial_number, kind)
    except Exception as e:
        raise HTTPException(502, str(e))