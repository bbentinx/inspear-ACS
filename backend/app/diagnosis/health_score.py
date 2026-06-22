"""Health Score 0-100 — pontuação de saúde do equipamento."""

from ..adapters.base import NormalizedDeviceState
from ..config import settings


def health_label(score: int) -> str:
    if score >= 90:
        return "healthy"
    if score >= 70:
        return "attention"
    if score >= 40:
        return "degraded"
    return "critical"


def calculate_health_score(state: NormalizedDeviceState) -> tuple[int, dict]:
    """
    Calcula health score e breakdown por componente.
    Pesos: óptico 25%, WAN/PPPoE 25%, IPv6/DNS 15%, Wi-Fi 15%, sistema 20%
    """
    breakdown: dict[str, float] = {}
    total = 100.0

    # Óptico (25 pts)
    optical = 25.0
    if state.optical_rx_power is not None:
        if state.optical_rx_power < settings.optical_rx_crit_dbm:
            optical = 0
        elif state.optical_rx_power < settings.optical_rx_warn_dbm:
            optical = 10
        elif state.optical_rx_power < -22:
            optical = 18
    else:
        optical = 15  # sem dado
    breakdown["optical"] = optical

    # WAN/PPPoE (25 pts)
    wan = 25.0
    if not state.is_online:
        wan = 0
    elif state.pppoe_status == "disconnected":
        wan = 5
    elif state.wan_status == "down":
        wan = 8
    breakdown["wan_pppoe"] = wan

    # IPv6 + DNS (15 pts)
    ip_dns = 15.0
    if state.ipv6_status in ("no_prefix", "disabled") and state.ipv4_address:
        ip_dns -= 8
    if state.dns_status in ("missing", "unreachable"):
        ip_dns -= 7
    breakdown["ipv6_dns"] = max(0, ip_dns)

    # Wi-Fi (15 pts)
    wifi = 15.0
    if state.wifi_clients_count >= settings.wifi_clients_crit:
        wifi = 3
    elif state.wifi_clients_count >= settings.wifi_clients_warn:
        wifi = 8
    if state.wifi_signal_avg is not None and state.wifi_signal_avg < -75:
        wifi = min(wifi, 5)
    breakdown["wifi"] = wifi

    # Sistema: uptime, reboots, CPU, memória (20 pts)
    system = 20.0
    if state.reboot_count_24h >= settings.reboot_crit_24h:
        system = 2
    elif state.reboot_count_24h >= settings.reboot_warn_24h:
        system = 10
    if state.cpu_usage and state.cpu_usage >= settings.cpu_warn_pct:
        system -= 5
    if state.memory_usage and state.memory_usage >= settings.memory_warn_pct:
        system -= 5
    if state.lan_status == "down":
        system -= 8
    breakdown["system"] = max(0, system)

    score = int(round(sum(breakdown.values())))
    score = max(0, min(100, score))
    return score, breakdown