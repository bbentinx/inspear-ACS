"""Provisionamento e restore remoto de ONTs — perfil desejado pós-reset."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.entities import Customer, Device, DeviceConfigProfile
from ..services.genieacs_client import genieacs_client


# TR-069 Huawei EG8145V5 — parâmetros para restore
MGMT = "InternetGatewayDevice.ManagementServer"
WAN_PPP = (
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1"
)
WLAN24 = "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1"
WLAN5 = "InternetGatewayDevice.LANDevice.1.WLANConfiguration.5"

def _profiles_dir() -> Path:
    base = Path(__file__).resolve().parent.parent.parent  # /app (docker) ou backend/
    for candidate in (base / "examples" / "profiles", base.parent / "examples" / "profiles"):
        if candidate.exists():
            return candidate
    return base.parent / "examples" / "profiles"
_CITY_CODES = {
    "fernandopolis": "fernandopolis-eg8145v5.json",
    "fernandópolis": "fernandopolis-eg8145v5.json",
}


def list_city_profiles() -> list[dict]:
    profiles = []
    for path in sorted(_profiles_dir().glob("*.json")):
        try:
            data = json.loads(path.read_text())
            profiles.append({
                "code": data.get("code", path.stem),
                "city": data.get("city"),
                "model": data.get("model"),
                "wan_vlan": data.get("wan_vlan"),
                "description": data.get("description"),
                "file": path.name,
            })
        except Exception:
            continue
    return profiles


def load_city_profile(city_code: str) -> Optional[dict]:
    key = city_code.lower().strip()
    filename = _CITY_CODES.get(key) or f"{key}.json"
    path = _profiles_dir() / filename
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _acs_defaults() -> dict[str, Any]:
    return {
        "acs_url": settings.genieacs_cwmp_url,
        "acs_username": settings.genieacs_acs_user,
        "acs_password": settings.genieacs_acs_password,
        "cr_username": settings.genieacs_cr_user,
        "cr_password": settings.genieacs_cr_password,
        "periodic_inform_interval": 300,
    }


def profile_to_dict(p: DeviceConfigProfile, include_secrets: bool = False) -> dict:
    data = {
        "id": str(p.id),
        "device_id": str(p.device_id),
        "serial_number": p.serial_number,
        "acs_url": p.acs_url,
        "acs_username": p.acs_username,
        "cr_username": p.cr_username,
        "periodic_inform_interval": p.periodic_inform_interval,
        "pppoe_username": p.pppoe_username,
        "wan_vlan": p.wan_vlan,
        "wifi_24_ssid": p.wifi_24_ssid,
        "wifi_5_ssid": p.wifi_5_ssid,
        "auto_restore_enabled": p.auto_restore_enabled,
        "source": p.source,
        "last_captured_at": p.last_captured_at,
        "last_applied_at": p.last_applied_at,
        "has_pppoe_password": bool(p.pppoe_password),
        "has_wifi_24_password": bool(p.wifi_24_password),
        "has_wifi_5_password": bool(p.wifi_5_password),
    }
    if include_secrets:
        data.update({
            "acs_password": p.acs_password,
            "cr_password": p.cr_password,
            "pppoe_password": p.pppoe_password,
            "wifi_24_password": p.wifi_24_password,
            "wifi_5_password": p.wifi_5_password,
        })
    return data


def build_restore_parameters(profile: DeviceConfigProfile) -> list[tuple[str, Any, str]]:
    """Lista TR-069 (path, value, type) para setParameterValues."""
    params: list[tuple[str, Any, str]] = []

    def add(path: str, value: Any, xsd: str = "xsd:string"):
        if value is not None and value != "":
            params.append((path, value, xsd))

    # ACS — crítico para ONT voltar a falar com GenieACS após reset
    add(f"{MGMT}.URL", profile.acs_url)
    add(f"{MGMT}.Username", profile.acs_username)
    add(f"{MGMT}.Password", profile.acs_password)
    add(f"{MGMT}.ConnectionRequestUsername", profile.cr_username)
    add(f"{MGMT}.ConnectionRequestPassword", profile.cr_password)
    add(f"{MGMT}.PeriodicInformEnable", True, "xsd:boolean")
    add(f"{MGMT}.PeriodicInformInterval", profile.periodic_inform_interval, "xsd:unsignedInt")

    # PPPoE discado
    add(f"{WAN_PPP}.Enable", True, "xsd:boolean")
    add(f"{WAN_PPP}.Username", profile.pppoe_username)
    add(f"{WAN_PPP}.Password", profile.pppoe_password)
    if profile.wan_vlan is not None:
        add(f"{WAN_PPP}.X_HW_VLAN", profile.wan_vlan, "xsd:unsignedInt")

    # Wi-Fi 2.4 GHz
    if profile.wifi_24_ssid:
        add(f"{WLAN24}.Enable", True, "xsd:boolean")
        add(f"{WLAN24}.SSID", profile.wifi_24_ssid)
        add(f"{WLAN24}.KeyPassphrase", profile.wifi_24_password)

    # Wi-Fi 5 GHz
    if profile.wifi_5_ssid:
        add(f"{WLAN5}.Enable", True, "xsd:boolean")
        add(f"{WLAN5}.SSID", profile.wifi_5_ssid)
        add(f"{WLAN5}.KeyPassphrase", profile.wifi_5_password)

    return params


def build_provision_payload(profile: DeviceConfigProfile) -> dict:
    """Payload para provision GenieACS (BOOT) — apenas paths com valor."""
    return {
        "serial_number": profile.serial_number,
        "auto_restore": profile.auto_restore_enabled,
        "parameters": [
            {"path": p, "value": v, "type": t}
            for p, v, t in build_restore_parameters(profile)
        ],
    }


async def get_profile_by_serial(db: AsyncSession, serial: str) -> Optional[DeviceConfigProfile]:
    r = await db.execute(
        select(DeviceConfigProfile).where(DeviceConfigProfile.serial_number == serial)
    )
    return r.scalar_one_or_none()


async def get_profile_by_device(db: AsyncSession, device_id) -> Optional[DeviceConfigProfile]:
    r = await db.execute(
        select(DeviceConfigProfile).where(DeviceConfigProfile.device_id == device_id)
    )
    return r.scalar_one_or_none()


async def apply_city_profile_to_device(
    db: AsyncSession,
    device: Device,
    city_code: str = "fernandopolis",
    customer: Optional[Customer] = None,
) -> DeviceConfigProfile:
    """Aplica template de cidade (ex: Fernandópolis VLAN 10) ao perfil da ONT."""
    template = load_city_profile(city_code)
    if not template:
        raise ValueError(f"Perfil de cidade não encontrado: {city_code}")

    profile = await get_profile_by_device(db, device.id)
    now = datetime.now(timezone.utc)
    if not profile:
        profile = DeviceConfigProfile(
            device_id=device.id,
            serial_number=device.serial_number,
            source="city_template",
        )
        db.add(profile)

    for field in (
        "acs_url", "acs_username", "acs_password", "cr_username", "cr_password",
        "periodic_inform_interval", "wan_vlan", "wifi_24_ssid", "wifi_5_ssid",
        "wifi_24_password", "wifi_5_password", "pppoe_username", "pppoe_password",
        "auto_restore_enabled",
    ):
        val = template.get(field)
        if val is not None:
            setattr(profile, field, val)

    if customer and customer.pppoe_login and not profile.pppoe_username:
        profile.pppoe_username = customer.pppoe_login

    profile.serial_number = device.serial_number
    profile.source = f"city:{template.get('code', city_code)}"
    profile.last_captured_at = now
    profile.updated_at = now
    await db.flush()
    return profile


async def capture_profile_from_state(
    db: AsyncSession,
    device: Device,
    normalized: dict,
    customer: Optional[Customer] = None,
) -> DeviceConfigProfile:
    """Salva/atualiza perfil a partir do snapshot normalizado (quando ONT está OK)."""
    profile = await get_profile_by_device(db, device.id)
    defaults = _acs_defaults()
    now = datetime.now(timezone.utc)

    networks = normalized.get("wifi_networks") or []
    wifi_24 = next((n for n in networks if n.get("index") == 1 or "2.4" in str(n.get("band", ""))), None)
    wifi_5 = next((n for n in networks if n.get("index") == 5 or "5" in str(n.get("band", ""))), None)

    pppoe_user = normalized.get("pppoe_username") or (customer.pppoe_login if customer else None)

    if not profile:
        try:
            profile = await apply_city_profile_to_device(db, device, "fernandopolis", customer)
        except ValueError:
            profile = DeviceConfigProfile(
                device_id=device.id,
                serial_number=device.serial_number,
                source="auto",
                wan_vlan=10,
                **_acs_defaults(),
            )
            db.add(profile)

    profile.serial_number = device.serial_number
    if profile.wan_vlan is None:
        profile.wan_vlan = 10
    profile.acs_url = profile.acs_url or defaults["acs_url"]
    profile.acs_username = profile.acs_username or defaults["acs_username"]
    profile.acs_password = profile.acs_password or defaults["acs_password"]
    profile.cr_username = profile.cr_username or defaults["cr_username"]
    profile.cr_password = profile.cr_password or defaults["cr_password"]
    profile.periodic_inform_interval = profile.periodic_inform_interval or defaults["periodic_inform_interval"]

    if pppoe_user:
        profile.pppoe_username = pppoe_user

    if wifi_24 and wifi_24.get("ssid"):
        profile.wifi_24_ssid = wifi_24["ssid"]
    elif normalized.get("wifi_ssid") and not profile.wifi_24_ssid:
        profile.wifi_24_ssid = normalized.get("wifi_ssid")

    if wifi_5 and wifi_5.get("ssid"):
        profile.wifi_5_ssid = wifi_5["ssid"]

    profile.last_captured_at = now
    profile.updated_at = now
    await db.flush()
    return profile


async def apply_restore_config(
    db: AsyncSession,
    device: Device,
    profile: Optional[DeviceConfigProfile] = None,
    trigger: str = "manual",
) -> dict:
    """Envia configuração desejada à ONT via GenieACS TR-069."""
    profile = profile or await get_profile_by_device(db, device.id)
    if not profile:
        return {"ok": False, "error": "Perfil de configuração não encontrado — capture ou cadastre primeiro"}

    if not profile.auto_restore_enabled and trigger == "auto":
        return {"ok": False, "error": "Auto-restore desabilitado para este equipamento"}

    params = build_restore_parameters(profile)
    if not params:
        return {"ok": False, "error": "Perfil vazio — informe PPPoE e/ou Wi-Fi"}

    missing = []
    if profile.pppoe_username and not profile.pppoe_password:
        missing.append("senha PPPoE")
    if profile.wifi_24_ssid and not profile.wifi_24_password:
        missing.append("senha Wi-Fi 2.4G")
    if profile.wifi_5_ssid and not profile.wifi_5_password:
        missing.append("senha Wi-Fi 5G")

    task = await genieacs_client.set_parameter_values(device.serial_number, params)
    try:
        await genieacs_client.connection_request(device.serial_number)
    except Exception:
        pass

    profile.last_applied_at = datetime.now(timezone.utc)
    profile.updated_at = datetime.now(timezone.utc)
    await db.flush()

    return {
        "ok": True,
        "trigger": trigger,
        "parameters_sent": len(params),
        "missing_secrets": missing,
        "task": task,
        "message": "Configuração enviada à ONT" + (
            f" — faltam: {', '.join(missing)}" if missing else ""
        ),
    }


BACKUP_POINT = (
    "InternetGatewayDevice.DeviceInfo.X_HW_AutoBackupRestore.AutoBackupRestorePoint"
)

# EG8145V5: parâmetro é xsd:unsignedInt (0 = sem backup). Valores 1–3 disparam gravação.
_BACKUP_TRIGGER_VALUES = (1, 2, 3)


def _read_backup_point_from_doc(doc: dict) -> Optional[int]:
    try:
        val = (
            doc["InternetGatewayDevice"]["DeviceInfo"]["X_HW_AutoBackupRestore"]
            ["AutoBackupRestorePoint"]["_value"]
        )
        return int(val) if val is not None else None
    except (KeyError, TypeError, ValueError):
        return None


async def read_backup_point(serial: str) -> Optional[int]:
    doc = await genieacs_client.get_device_by_serial(serial)
    if not doc:
        return None
    return _read_backup_point_from_doc(doc)


async def save_isp_default_on_device(
    db: AsyncSession,
    device: Device,
    profile: Optional[DeviceConfigProfile] = None,
) -> dict:
    """
    Grava padrão ISP na ONT:
    1) Aplica parâmetros TR-069 (PPPoE VLAN 10, ACS, Wi-Fi)
    2) Gera e envia Vendor Configuration File
    3) Dispara backup/restore point Huawei
    """
    import asyncio

    profile = profile or await get_profile_by_device(db, device.id)
    if not profile:
        return {"ok": False, "error": "Perfil não encontrado — aplique Padrão Fernandópolis e preencha senhas"}

    missing = []
    if not profile.pppoe_username:
        missing.append("usuário PPPoE")
    if not profile.pppoe_password:
        missing.append("senha PPPoE")
    if not profile.wifi_24_password and profile.wifi_24_ssid:
        missing.append("senha Wi-Fi 2.4G")
    if not profile.wifi_5_password and profile.wifi_5_ssid:
        missing.append("senha Wi-Fi 5G")
    if missing:
        return {
            "ok": False,
            "error": f"Perfil incompleto: {', '.join(missing)}",
            "hint": "Preencha senha PPPoE e Wi-Fi no card Restore remoto antes de gravar",
        }

    params = build_restore_parameters(profile)
    steps: list[dict] = []

    # 1) Aplicar configuração ativa
    task_set = await genieacs_client.set_parameter_values(device.serial_number, params)
    steps.append({"step": "setParameterValues", "params": len(params), "task": task_set})
    try:
        await genieacs_client.connection_request(device.serial_number)
    except Exception:
        pass
    await asyncio.sleep(5)

    # 2) Download Vendor Configuration File (XML servido pela API)
    vendor_url = (
        f"{settings.public_api_base_url.rstrip('/')}"
        f"/api/v1/acs/vendor-file/{profile.serial_number}.xml"
    )
    try:
        task_dl = await genieacs_client.download_vendor_config(
            device.serial_number, vendor_url, f"inspear-{profile.serial_number}.xml"
        )
        steps.append({"step": "vendorConfigDownload", "url": vendor_url, "task": task_dl})
    except Exception as e:
        steps.append({"step": "vendorConfigDownload", "error": str(e)})
    await asyncio.sleep(8)

    # 3) Gravar ponto de backup Huawei (auto-restore após reset físico)
    backup_before = await read_backup_point(device.serial_number)
    backup_results = []
    backup_value: Optional[int] = None
    for val in _BACKUP_TRIGGER_VALUES:
        try:
            t = await genieacs_client.set_parameter_values(
                device.serial_number,
                [(BACKUP_POINT, val, "xsd:unsignedInt")],
            )
            backup_results.append({"value": val, "task": t})
            backup_value = val
            break
        except Exception as e:
            backup_results.append({"value": val, "error": str(e)})

    steps.append({
        "step": "autoBackupRestorePoint",
        "before": backup_before,
        "attempts": backup_results,
    })
    try:
        await genieacs_client.connection_request(device.serial_number)
    except Exception:
        pass
    await asyncio.sleep(6)
    backup_after = await read_backup_point(device.serial_number)
    backup_verified = backup_after is not None and backup_after > 0
    steps.append({
        "step": "autoBackupRestorePointVerify",
        "value": backup_after,
        "verified": backup_verified,
    })

    profile.last_applied_at = datetime.now(timezone.utc)
    profile.updated_at = datetime.now(timezone.utc)
    profile.source = "isp_default_saved" if backup_verified else "isp_default_partial"
    await db.flush()

    if backup_verified:
        message = (
            f"Padrão ISP gravado na flash (backup #{backup_after}) — "
            f"VLAN {profile.wan_vlan}, PPPoE {profile.pppoe_username}"
        )
        test_hint = "Reset físico: aguarde ~3 min — deve restaurar sozinho"
    else:
        message = (
            f"Config aplicada (VLAN {profile.wan_vlan}, PPPoE {profile.pppoe_username}), "
            "mas backup na flash NÃO confirmado — reset físico pode apagar tudo"
        )
        test_hint = (
            "Após reset físico: configure ACS URL manualmente em 192.168.100.1 "
            "ou use OLT/DHCP option 43 — depois o Inspear restaura o resto"
        )

    return {
        "ok": True,
        "backup_verified": backup_verified,
        "backup_point": backup_after,
        "message": message,
        "vendor_url": vendor_url,
        "steps": steps,
        "test_hint": test_hint,
        "reset_note": (
            "Reset pelo botão apaga TR-069. Sem backup na flash (valor > 0), "
            "a ONT não fala com o GenieACS até o ACS URL ser configurado de novo."
        ),
    }


def looks_like_factory_reset(normalized: dict) -> bool:
    """Heurística: uptime baixo + PPPoE down ou SSID padrão Huawei."""
    uptime = normalized.get("uptime_seconds") or 0
    pppoe = str(normalized.get("pppoe_status") or "").lower()
    ssids = [n.get("ssid", "") for n in (normalized.get("wifi_networks") or [])]
    has_custom_ssid = any(
        ssid and not any(p in ssid.lower() for p in ("huawei", "eg8145", "ont_", "unknown"))
        for ssid in ssids
    )
    return uptime < 600 and (
        pppoe not in ("connected", "up")
        or not has_custom_ssid
    )