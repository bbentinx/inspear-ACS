"""Ações TR-069 via GenieACS — Wi-Fi, ping, speed test."""

from typing import Any, Optional
from ..config import settings
from .genieacs_client import genieacs_client
from .wan_counters import (
    diagnostics_completed_after_baseline,
    get_baseline,
    snapshot_baseline,
    wan_throughput_from_baseline,
    _tr069_duration_seconds,
)

WLAN_REFRESH_PATHS = [
    "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.TotalAssociations",
    "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.SSID",
    "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.Channel",
    "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.BeaconType",
    "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.AssociatedDevice",
    "InternetGatewayDevice.LANDevice.1.WLANConfiguration.5.TotalAssociations",
    "InternetGatewayDevice.LANDevice.1.WLANConfiguration.5.SSID",
    "InternetGatewayDevice.LANDevice.1.WLANConfiguration.5.Channel",
    "InternetGatewayDevice.LANDevice.1.WLANConfiguration.5.BeaconType",
    "InternetGatewayDevice.LANDevice.1.WLANConfiguration.5.AssociatedDevice",
]

NBI_SYNC_REFRESH_PATHS = WLAN_REFRESH_PATHS + [
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.ConnectionStatus",
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.Username",
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.ExternalIPAddress",
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.X_HW_VLAN",
    "InternetGatewayDevice.WANDevice.1.X_GponInterafceConfig.RXPower",
    "InternetGatewayDevice.WANDevice.1.X_GponInterafceConfig.TXPower",
    "InternetGatewayDevice.DeviceInfo.X_HW_CpuUsed",
    "InternetGatewayDevice.DeviceInfo.X_HW_MemUsed",
    "InternetGatewayDevice.DownloadDiagnostics.DiagnosticsState",
    "InternetGatewayDevice.DownloadDiagnostics.TestBytesReceived",
    "InternetGatewayDevice.UploadDiagnostics.DiagnosticsState",
    "InternetGatewayDevice.UploadDiagnostics.TotalBytesSent",
]

PING_RESULT_PATHS = [
    "InternetGatewayDevice.IPPingDiagnostics.DiagnosticsState",
    "InternetGatewayDevice.IPPingDiagnostics.Host",
    "InternetGatewayDevice.IPPingDiagnostics.SuccessCount",
    "InternetGatewayDevice.IPPingDiagnostics.FailureCount",
    "InternetGatewayDevice.IPPingDiagnostics.AverageResponseTime",
    "InternetGatewayDevice.IPPingDiagnostics.MinimumResponseTime",
    "InternetGatewayDevice.IPPingDiagnostics.MaximumResponseTime",
]

SPEED_RESULT_PATHS = [
    "InternetGatewayDevice.DownloadDiagnostics.DiagnosticsState",
    "InternetGatewayDevice.DownloadDiagnostics.DownloadURL",
    "InternetGatewayDevice.DownloadDiagnostics.TestBytesReceived",
    "InternetGatewayDevice.DownloadDiagnostics.TotalBytesReceived",
    "InternetGatewayDevice.DownloadDiagnostics.BOMTime",
    "InternetGatewayDevice.DownloadDiagnostics.EOMTime",
]

UPLOAD_RESULT_PATHS = [
    "InternetGatewayDevice.UploadDiagnostics.DiagnosticsState",
    "InternetGatewayDevice.UploadDiagnostics.UploadURL",
    "InternetGatewayDevice.UploadDiagnostics.TestFileLength",
    "InternetGatewayDevice.UploadDiagnostics.TotalBytesSent",
    "InternetGatewayDevice.UploadDiagnostics.BOMTime",
    "InternetGatewayDevice.UploadDiagnostics.EOMTime",
]

TRACEROUTE_RESULT_PATHS = [
    "InternetGatewayDevice.TraceRouteDiagnostics.DiagnosticsState",
    "InternetGatewayDevice.TraceRouteDiagnostics.Host",
    "InternetGatewayDevice.TraceRouteDiagnostics.ResponseTime",
    "InternetGatewayDevice.TraceRouteDiagnostics.NumberOfTries",
    "InternetGatewayDevice.TraceRouteDiagnostics.RouteHopsNumberOfEntries",
]

SOCIAL_PING_HOSTS = {
    "instagram": "instagram.com",
    "facebook": "facebook.com",
    "whatsapp": "web.whatsapp.com",
    "tiktok": "tiktok.com",
    "youtube": "youtube.com",
    "dns_google": "8.8.8.8",
    "dns_cloudflare": "1.1.1.1",
}


def _wlan_base(index: int) -> str:
    return f"InternetGatewayDevice.LANDevice.1.WLANConfiguration.{index}"


def _vendor_from_doc(doc: dict | None) -> str:
    if not doc:
        return "generic"
    did = doc.get("_deviceId") or {}
    mfr = str(did.get("_Manufacturer", "")).lower()
    model = str(did.get("_ProductClass") or _scalar(_get_param_from_doc(
        doc, "InternetGatewayDevice.DeviceInfo.ModelName"
    )) or "").lower()
    if "realtek" in mfr or model == "igd":
        return "realtek"
    if "huawei" in mfr or "eg8145" in model or "hg8245" in model:
        return "huawei"
    return "generic"


def _get_param_from_doc(doc: dict, path: str) -> Any:
    cur: Any = doc
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return _scalar(cur)


async def refresh_wifi_stats(serial: str) -> dict:
    await genieacs_client.get_parameter_values(serial, WLAN_REFRESH_PATHS + [
        "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.BeaconType",
        "InternetGatewayDevice.LANDevice.1.WLANConfiguration.5.BeaconType",
    ])
    try:
        await genieacs_client.connection_request(serial)
    except Exception:
        pass
    return {"status": "requested", "message": "Coleta Wi-Fi solicitada à ONT"}


async def update_wifi(
    serial: str,
    wlan_index: int = 1,
    ssid: Optional[str] = None,
    password: Optional[str] = None,
    open_network: bool = False,
) -> dict:
    doc = await genieacs_client.get_device_by_serial(serial)
    vendor = _vendor_from_doc(doc)

    params: list[tuple[str, Any, str]] = []
    base = _wlan_base(wlan_index)
    params.append((f"{base}.Enable", True, "xsd:boolean"))
    if ssid is not None and ssid != "":
        params.append((f"{base}.SSID", ssid, "xsd:string"))
    if open_network:
        if vendor == "realtek":
            # Realtek IGD V2.0.03 — BasicAuthenticationMode Both (não None)
            params.extend([
                (f"{base}.BeaconType", "Basic", "xsd:string"),
                (f"{base}.BasicAuthenticationMode", "Both", "xsd:string"),
                (f"{base}.BasicEncryptionModes", "None", "xsd:string"),
                (f"{base}.KeyPassphrase", "", "xsd:string"),
                (f"{base}.PreSharedKey.1.KeyPassphrase", "", "xsd:string"),
            ])
        else:
            # Huawei EG8145V5 — não usar WPAEncryptionModes=None (9007)
            params.extend([
                (f"{base}.BeaconType", "Basic", "xsd:string"),
                (f"{base}.BasicAuthenticationMode", "None", "xsd:string"),
                (f"{base}.BasicEncryptionModes", "None", "xsd:string"),
                (f"{base}.KeyPassphrase", "", "xsd:string"),
                (f"{base}.PreSharedKey.1.KeyPassphrase", "", "xsd:string"),
            ])
    elif password is not None and password != "":
        wpa_mode = "TKIPEncryption" if vendor == "realtek" else "TKIPandAESEncryption"
        params.extend([
            (f"{base}.BeaconType", "WPAand11i", "xsd:string"),
            (f"{base}.WPAEncryptionModes", wpa_mode, "xsd:string"),
            (f"{base}.BasicEncryptionModes", "None", "xsd:string"),
            (f"{base}.KeyPassphrase", password, "xsd:string"),
            (f"{base}.PreSharedKey.1.KeyPassphrase", password, "xsd:string"),
        ])
    if len(params) <= 1:
        return {"status": "noop", "message": "Informe SSID, senha ou marque rede aberta"}
    task = await genieacs_client.set_parameter_values(serial, params)
    cr_ok = True
    try:
        await genieacs_client.connection_request(serial)
    except Exception:
        cr_ok = False
    label = ssid or f"WLAN {wlan_index}"
    mode = "aberta" if open_network else "com senha" if password else "SSID"
    msg = f"Wi-Fi enfileirado ({mode}): {label}"
    if not cr_ok:
        msg += " — Connection Request indisponível; confira CR user/senha na ONT (aplica no próximo Inform)"
    return {"status": "ok", "task": task, "connection_request": cr_ok, "message": msg}


async def start_ping_test(serial: str, host: str, count: int = 4) -> dict:
    prefix = "InternetGatewayDevice.IPPingDiagnostics"
    params = [
        (f"{prefix}.Host", host, "xsd:string"),
        (f"{prefix}.NumberOfRepetitions", count, "xsd:unsignedInt"),
        (f"{prefix}.Timeout", 3000, "xsd:unsignedInt"),
        (f"{prefix}.DiagnosticsState", "Requested", "xsd:string"),
    ]
    task = await genieacs_client.set_parameter_values(serial, params)
    try:
        await genieacs_client.connection_request(serial)
    except Exception:
        pass
    return {
        "status": "running",
        "host": host,
        "task": task,
        "message": f"Ping para {host} iniciado na ONT — aguarde ~30s e consulte resultado",
    }


async def start_upload_test(
    serial: str,
    upload_url: str | None = None,
    file_size: int = 10485760,
) -> dict:
    await snapshot_baseline(serial, "upload")
    upload_url = upload_url or settings.speed_test_upload_url
    prefix = "InternetGatewayDevice.UploadDiagnostics"
    params = [
        (f"{prefix}.UploadURL", upload_url, "xsd:string"),
        (f"{prefix}.TestFileLength", file_size, "xsd:unsignedInt"),
        (f"{prefix}.DiagnosticsState", "Requested", "xsd:string"),
    ]
    task = await genieacs_client.set_parameter_values(serial, params)
    try:
        await genieacs_client.connection_request(serial)
    except Exception:
        pass
    return {"status": "running", "url": upload_url, "task": task, "message": "Teste de upload iniciado na ONT"}


async def start_traceroute(serial: str, host: str, max_hops: int = 8) -> dict:
    prefix = "InternetGatewayDevice.TraceRouteDiagnostics"
    params = [
        (f"{prefix}.Host", host, "xsd:string"),
        (f"{prefix}.MaxHopCount", max_hops, "xsd:unsignedInt"),
        (f"{prefix}.NumberOfTries", 3, "xsd:unsignedInt"),
        (f"{prefix}.Timeout", 3000, "xsd:unsignedInt"),
        (f"{prefix}.DiagnosticsState", "Requested", "xsd:string"),
    ]
    task = await genieacs_client.set_parameter_values(serial, params)
    try:
        await genieacs_client.connection_request(serial)
    except Exception:
        pass
    return {"status": "running", "host": host, "task": task, "message": f"Traceroute para {host} iniciado na ONT"}


async def start_speed_test(
    serial: str,
    download_url: str | None = None,
) -> dict:
    await snapshot_baseline(serial, "download")
    download_url = download_url or settings.speed_test_download_url
    prefix = "InternetGatewayDevice.DownloadDiagnostics"
    # Huawei EG8145V5: limpar estado anterior antes de novo teste
    await genieacs_client.set_parameter_values(
        serial, [(f"{prefix}.DiagnosticsState", "None", "xsd:string")]
    )
    params = [
        (f"{prefix}.DownloadURL", download_url, "xsd:string"),
        (f"{prefix}.DiagnosticsState", "Requested", "xsd:string"),
    ]
    task = await genieacs_client.set_parameter_values(serial, params)
    try:
        await genieacs_client.connection_request(serial)
    except Exception:
        pass
    return {
        "status": "running",
        "url": download_url,
        "task": task,
        "message": "Teste de download iniciado na ONT — aguarde e consulte resultado",
    }


def _scalar(val: Any) -> Any:
    """GenieACS pode retornar {_value: X} em vez de escalar."""
    if val is None:
        return None
    if isinstance(val, dict):
        if "_value" in val:
            return val["_value"]
        return None
    return val


def _to_float(val: Any) -> float | None:
    v = _scalar(val)
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _calc_speed_mbps(bytes_val, start, end) -> float | None:
    try:
        b = _to_float(bytes_val)
        start_s = _scalar(start)
        end_s = _scalar(end)
        if b is None or not start_s or not end_s:
            return None
        from datetime import datetime
        t0 = datetime.fromisoformat(str(start_s).replace("Z", "+00:00"))
        t1 = datetime.fromisoformat(str(end_s).replace("Z", "+00:00"))
        secs = max((t1 - t0).total_seconds(), 0.001)
        return round((b * 8) / secs / 1_000_000, 1)
    except Exception:
        return None


async def read_diagnostic_results(serial: str, kind: str = "ping") -> dict:
    from .genieacs import _get_param, extract_wifi_stats

    path_map = {
        "ping": PING_RESULT_PATHS,
        "speed": SPEED_RESULT_PATHS,
        "upload": UPLOAD_RESULT_PATHS,
        "traceroute": TRACEROUTE_RESULT_PATHS,
    }
    paths = path_map.get(kind, PING_RESULT_PATHS)
    try:
        await genieacs_client.get_parameter_values(serial, paths)
        await genieacs_client.connection_request(serial)
    except Exception:
        pass

    doc = await genieacs_client.get_device_by_serial(serial)
    if not doc:
        return {"error": "ONT não encontrada no GenieACS"}

    results = {p.split(".")[-1]: _scalar(_get_param(doc, p)) for p in paths}

    payload: dict = {"kind": kind, "results": results, "state": results.get("DiagnosticsState")}
    if kind == "speed":
        bytes_val = _to_float(results.get("TestBytesReceived"))
        payload["download_mbps"] = _calc_speed_mbps(
            results.get("TestBytesReceived"),
            results.get("BOMTime"),
            results.get("EOMTime"),
        )
        payload["bytes_mb"] = round(bytes_val / 1_048_576, 2) if bytes_val else None
        payload["tr069_mbps"] = payload["download_mbps"]
        baseline = get_baseline(serial, "download")
        test_done = bool(baseline and diagnostics_completed_after_baseline(results, baseline))
        wan = await wan_throughput_from_baseline(
            serial,
            "download",
            refresh=not test_done,
            wait_for_update=False,
            tr069_duration_s=_tr069_duration_seconds(results) if test_done else None,
        )
        payload["wan_download_mbps"] = wan.get("wan_mbps")
        payload["wan_bytes_mb"] = wan.get("wan_bytes_mb")
        payload["wan_counter"] = wan.get("counter_param")
        payload["wan_available"] = wan.get("available", False)
        payload["wan_test_done"] = test_done
    if kind == "upload":
        bytes_val = _to_float(results.get("TotalBytesSent"))
        payload["upload_mbps"] = _calc_speed_mbps(
            results.get("TotalBytesSent"),
            results.get("BOMTime"),
            results.get("EOMTime"),
        )
        payload["bytes_mb"] = round(bytes_val / 1_048_576, 2) if bytes_val else None
        payload["tr069_mbps"] = payload["upload_mbps"]
        baseline = get_baseline(serial, "upload")
        test_done = bool(baseline and diagnostics_completed_after_baseline(results, baseline))
        wan = await wan_throughput_from_baseline(
            serial,
            "upload",
            refresh=not test_done,
            wait_for_update=False,
            tr069_duration_s=_tr069_duration_seconds(results) if test_done else None,
        )
        payload["wan_upload_mbps"] = wan.get("wan_mbps")
        payload["wan_bytes_mb"] = wan.get("wan_bytes_mb")
        payload["wan_counter"] = wan.get("counter_param")
        payload["wan_available"] = wan.get("available", False)
        payload["wan_test_done"] = test_done
    if kind == "ping":
        for key in ("AverageResponseTime", "MinimumResponseTime", "MaximumResponseTime"):
            results[key] = _to_float(results.get(key))
    if kind == "wifi":
        payload["wifi"] = extract_wifi_stats(doc)
    return payload