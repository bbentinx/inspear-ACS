"""Medição de banda via contadores WAN (TR-069) — Huawei EG8145V5 e similares."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Literal

from .genieacs import _get_param
from .genieacs_client import genieacs_client

Direction = Literal["download", "upload"]

# Contadores WAN — PPP preferido; WANCommon como fallback
WAN_RX_PATHS = [
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.Stats.EthernetBytesReceived",
    "InternetGatewayDevice.WANDevice.1.WANCommonInterfaceConfig.TotalBytesReceived",
    "InternetGatewayDevice.WANDevice.1.X_GponInterafceConfig.Stats.BytesReceived",
]
WAN_TX_PATHS = [
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.Stats.EthernetBytesSent",
    "InternetGatewayDevice.WANDevice.1.WANCommonInterfaceConfig.TotalBytesSent",
    "InternetGatewayDevice.WANDevice.1.X_GponInterafceConfig.Stats.BytesSent",
]

WAN_COUNTER_PATHS = list(dict.fromkeys(WAN_RX_PATHS + WAN_TX_PATHS))

WAN_REFRESH_OBJECTS = [
    "InternetGatewayDevice.WANDevice.1.WANCommonInterfaceConfig.",
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.Stats.",
    "InternetGatewayDevice.WANDevice.1.X_GponInterafceConfig.Stats.",
]

# baseline por serial+direction durante teste de velocidade
_baselines: dict[str, dict] = {}


def _baseline_key(serial: str, direction: Direction) -> str:
    return f"{serial}:{direction}"


def _scalar(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, dict) and "_value" in val:
        return val["_value"]
    return val


def _to_int(val: Any) -> int | None:
    v = _scalar(val)
    if v is None or v == "":
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _first_counter(doc: dict, paths: list[str]) -> tuple[int | None, str | None]:
    for path in paths:
        val = _to_int(_get_param(doc, path))
        if val is not None:
            return val, path.split(".")[-1]
    return None, None


def calc_throughput_mbps(
    bytes_start: int,
    bytes_end: int,
    ts_start: datetime,
    ts_end: datetime,
) -> float | None:
    delta_bytes = bytes_end - bytes_start
    if delta_bytes <= 0:
        return None
    secs = max((ts_end - ts_start).total_seconds(), 0.001)
    return round((delta_bytes * 8) / secs / 1_000_000, 1)


async def _refresh_wan_stats(serial: str) -> None:
    paths = WAN_COUNTER_PATHS
    try:
        await genieacs_client.get_parameter_values(serial, paths)
    except Exception:
        pass
    for obj in WAN_REFRESH_OBJECTS:
        try:
            await genieacs_client.refresh_object(serial, obj)
        except Exception:
            pass
    try:
        await genieacs_client.connection_request(serial)
    except Exception:
        pass


def _counter_timestamp(doc: dict) -> str | None:
    for path in WAN_RX_PATHS:
        parts = path.split(".")
        cur: Any = doc
        for part in parts:
            if not isinstance(cur, dict) or part not in cur:
                cur = None
                break
            cur = cur[part]
        if isinstance(cur, dict) and cur.get("_timestamp"):
            return str(cur["_timestamp"])
    return None


async def read_wan_counters(
    serial: str,
    *,
    refresh: bool = True,
    wait_for_update: bool = False,
    wait_timeout_s: float = 36.0,
) -> dict:
    """Lê contadores RX/TX da interface WAN."""
    old_ts = None
    if wait_for_update:
        doc0 = await genieacs_client.get_device_by_serial(serial)
        if doc0:
            old_ts = _counter_timestamp(doc0)

    if refresh:
        await _refresh_wan_stats(serial)

    if wait_for_update and old_ts:
        elapsed = 0.0
        while elapsed < wait_timeout_s:
            await asyncio.sleep(3.0)
            elapsed += 3.0
            doc = await genieacs_client.get_device_by_serial(serial)
            if doc and _counter_timestamp(doc) and _counter_timestamp(doc) != old_ts:
                break

    doc = await genieacs_client.get_device_by_serial(serial)
    if not doc:
        return {"available": False, "error": "ONT não encontrada no GenieACS"}

    rx, rx_param = _first_counter(doc, WAN_RX_PATHS)
    tx, tx_param = _first_counter(doc, WAN_TX_PATHS)
    now = datetime.now(timezone.utc)

    return {
        "available": rx is not None or tx is not None,
        "bytes_rx": rx,
        "bytes_tx": tx,
        "rx_param": rx_param,
        "tx_param": tx_param,
        "sampled_at": now.isoformat(),
    }


async def snapshot_baseline(serial: str, direction: Direction) -> dict:
    """Grava contador WAN no início de um teste de velocidade."""
    counters = await read_wan_counters(serial)
    key = _baseline_key(serial, direction)
    now = datetime.now(timezone.utc)
    byte_key = "bytes_rx" if direction == "download" else "bytes_tx"
    _baselines[key] = {
        "direction": direction,
        "bytes": counters.get(byte_key),
        "param": counters.get("rx_param" if direction == "download" else "tx_param"),
        "sampled_at": now,
        "counters": counters,
        "seen_requested": False,
    }
    return _baselines[key]


def get_baseline(serial: str, direction: Direction) -> dict | None:
    return _baselines.get(_baseline_key(serial, direction))


def clear_baseline(serial: str, direction: Direction) -> None:
    _baselines.pop(_baseline_key(serial, direction), None)


def mark_baseline_phase(baseline: dict, results: dict) -> None:
    """Rastreia se a ONT já aceitou o novo teste (Requested/InProgress)."""
    state = str(results.get("DiagnosticsState") or "")
    if state in ("Requested", "InProgress"):
        baseline["seen_requested"] = True


def diagnostics_completed_after_baseline(results: dict, baseline: dict) -> bool:
    """Evita limpar baseline com resultado TR-069 de teste anterior."""
    mark_baseline_phase(baseline, results)
    if str(results.get("DiagnosticsState") or "") not in ("Completed", "Complete"):
        return False
    if not baseline.get("seen_requested"):
        return False

    bom = results.get("BOMTime")
    eom = results.get("EOMTime")
    if bom and eom:
        try:
            t0 = datetime.fromisoformat(str(bom).replace("Z", "+00:00"))
            t1 = datetime.fromisoformat(str(eom).replace("Z", "+00:00"))
            if (t1 - t0).total_seconds() > 0:
                return True
        except Exception:
            pass

    for key in ("TestBytesReceived", "TotalBytesSent"):
        val = results.get(key)
        if val is not None:
            try:
                if float(val) >= 1_000_000:
                    return True
            except (TypeError, ValueError):
                pass
    return False


def _tr069_duration_seconds(results: dict) -> float | None:
    bom = results.get("BOMTime")
    eom = results.get("EOMTime")
    if not bom or not eom:
        return None
    try:
        t0 = datetime.fromisoformat(str(bom).replace("Z", "+00:00"))
        t1 = datetime.fromisoformat(str(eom).replace("Z", "+00:00"))
        secs = (t1 - t0).total_seconds()
        return secs if secs > 0 else None
    except Exception:
        return None


async def wan_throughput_from_baseline(
    serial: str,
    direction: Direction,
    *,
    refresh: bool = True,
    wait_for_update: bool = False,
    tr069_duration_s: float | None = None,
) -> dict:
    """Calcula Mbps WAN desde o baseline gravado no início do teste."""
    baseline = get_baseline(serial, direction)
    if not baseline or baseline.get("bytes") is None:
        return {
            "available": False,
            "wan_mbps": None,
            "reason": "baseline_indisponivel",
        }

    current = await read_wan_counters(
        serial,
        refresh=refresh,
        wait_for_update=wait_for_update,
    )
    byte_key = "bytes_rx" if direction == "download" else "bytes_tx"
    end_bytes = current.get(byte_key)
    if end_bytes is None:
        return {
            "available": False,
            "wan_mbps": None,
            "reason": "contador_indisponivel",
            "baseline": _serialize_baseline(baseline),
            "current": current,
        }

    ts_start = baseline["sampled_at"]
    if isinstance(ts_start, str):
        ts_start = datetime.fromisoformat(ts_start.replace("Z", "+00:00"))
    ts_end = datetime.fromisoformat(current["sampled_at"].replace("Z", "+00:00"))

    delta_bytes = end_bytes - baseline["bytes"]
    delta_mb = round(delta_bytes / 1_048_576, 2) if delta_bytes > 0 else None

    if tr069_duration_s and tr069_duration_s > 0 and delta_bytes > 0:
        wan_mbps = round((delta_bytes * 8) / tr069_duration_s / 1_000_000, 1)
        duration_s = tr069_duration_s
    else:
        wan_mbps = calc_throughput_mbps(baseline["bytes"], end_bytes, ts_start, ts_end)
        duration_s = (ts_end - ts_start).total_seconds()

    return {
        "available": wan_mbps is not None,
        "wan_mbps": wan_mbps,
        "wan_bytes_mb": delta_mb,
        "counter_param": baseline.get("param"),
        "duration_s": round(duration_s, 1),
        "baseline": _serialize_baseline(baseline),
        "current": current,
    }


async def sample_wan_throughput(
    serial: str,
    direction: Direction = "download",
    interval_s: float = 3.0,
) -> dict:
    """Amostra contadores WAN em dois instantes (útil fora do speed test TR-069)."""
    byte_key = "bytes_rx" if direction == "download" else "bytes_tx"
    first = await read_wan_counters(serial)
    if first.get(byte_key) is None:
        return {
            "available": False,
            "wan_mbps": None,
            "reason": "contador_indisponivel",
            "samples": [first],
        }

    await asyncio.sleep(interval_s)
    second = await read_wan_counters(serial)
    end_bytes = second.get(byte_key)
    if end_bytes is None:
        return {
            "available": False,
            "wan_mbps": None,
            "reason": "segunda_amostra_indisponivel",
            "samples": [first, second],
        }

    ts_start = datetime.fromisoformat(first["sampled_at"].replace("Z", "+00:00"))
    ts_end = datetime.fromisoformat(second["sampled_at"].replace("Z", "+00:00"))
    wan_mbps = calc_throughput_mbps(first[byte_key], end_bytes, ts_start, ts_end)

    return {
        "available": wan_mbps is not None,
        "direction": direction,
        "wan_mbps": wan_mbps,
        "interval_s": interval_s,
        "counter_param": first.get("rx_param" if direction == "download" else "tx_param"),
        "samples": [first, second],
    }


def _serialize_baseline(baseline: dict) -> dict:
    ts = baseline.get("sampled_at")
    if isinstance(ts, datetime):
        ts = ts.isoformat()
    return {
        "bytes": baseline.get("bytes"),
        "param": baseline.get("param"),
        "sampled_at": ts,
    }