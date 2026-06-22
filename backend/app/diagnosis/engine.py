"""Motor de diagnóstico por regras — analisa estado normalizado e gera diagnósticos."""

from dataclasses import dataclass, field
from typing import Optional

from ..adapters.base import NormalizedDeviceState
from ..config import settings
from .health_score import calculate_health_score, health_label


@dataclass
class DiagnosisResult:
    problem_code: str
    problem_label: str
    severity: str  # info, warn, crit
    confidence: float
    evidences: list[str] = field(default_factory=list)
    counter_evidences: list[str] = field(default_factory=list)
    recommended_action: str = ""
    responsible_team: str = "noc"  # support, noc, field, upstream


class DiagnosisEngine:
    """Motor de regras — extensível para ML futuro."""

    def analyze(self, state: NormalizedDeviceState, context: Optional[dict] = None) -> tuple[list[DiagnosisResult], int, str, dict]:
        """
        Retorna: (diagnósticos, health_score, health_status, breakdown)
        context pode incluir: pon_affected_count, pop_pppoe_issues, model_failure_rate
        """
        ctx = context or {}
        results: list[DiagnosisResult] = []

        # Regra: ONT offline
        if not state.is_online:
            results.append(DiagnosisResult(
                problem_code="ont_offline",
                problem_label="ONT offline",
                severity="crit",
                confidence=95,
                evidences=["Equipamento não respondeu ao último Inform/CWMP", "is_online = false"],
                recommended_action="Verificar energia, fibra, OLT e autorização da ONU. Checar se ONU está na OLT.",
                responsible_team="field",
            ))

        # Regra: Sinal óptico baixo
        if state.optical_rx_power is not None:
            if state.optical_rx_power < settings.optical_rx_crit_dbm:
                results.append(DiagnosisResult(
                    problem_code="optical_low_crit",
                    problem_label="Sinal óptico crítico",
                    severity="crit",
                    confidence=92,
                    evidences=[f"RX power = {state.optical_rx_power:.1f} dBm (limite crítico {settings.optical_rx_crit_dbm} dBm)"],
                    counter_evidences=["Verificar se leitura é momentânea ou sustentada"] if state.uptime_seconds and state.uptime_seconds > 3600 else [],
                    recommended_action="Acionar campo: verificar conector, drop, CTO, fusão e splitter. Medir potência na ONT.",
                    responsible_team="field",
                ))
            elif state.optical_rx_power < settings.optical_rx_warn_dbm:
                results.append(DiagnosisResult(
                    problem_code="optical_low_warn",
                    problem_label="Sinal óptico baixo",
                    severity="warn",
                    confidence=85,
                    evidences=[f"RX power = {state.optical_rx_power:.1f} dBm"],
                    recommended_action="Agendar verificação de conectores e perdas no drop. Monitorar tendência.",
                    responsible_team="field",
                ))

        # Regra: Muitos reboots
        if state.reboot_count_24h >= settings.reboot_crit_24h:
            results.append(DiagnosisResult(
                problem_code="reboot_loop",
                problem_label="Equipamento reiniciando frequentemente",
                severity="crit",
                confidence=88,
                evidences=[f"{state.reboot_count_24h} reinícios nas últimas 24h"],
                counter_evidences=[f"Motivo: {state.last_reboot_reason}"] if state.last_reboot_reason else [],
                recommended_action="Verificar fonte/energia, firmware, superaquecimento. Considerar troca da ONT.",
                responsible_team="field",
            ))
        elif state.reboot_count_24h >= settings.reboot_warn_24h:
            results.append(DiagnosisResult(
                problem_code="reboot_frequent",
                problem_label="Reinícios acima do normal",
                severity="warn",
                confidence=75,
                evidences=[f"{state.reboot_count_24h} reinícios em 24h"],
                recommended_action="Verificar histórico de energia e atualização de firmware.",
                responsible_team="support",
            ))

        # Regra: PPPoE caiu mas ONT online e sinal OK
        if (
            state.pppoe_status == "disconnected"
            and state.is_online
            and (state.optical_rx_power is None or state.optical_rx_power >= settings.optical_rx_warn_dbm)
        ):
            results.append(DiagnosisResult(
                problem_code="pppoe_auth_failure",
                problem_label="Falha PPPoE — autenticação/concentrador",
                severity="crit",
                confidence=82,
                evidences=["PPPoE desconectado", "ONT online", "Sinal óptico dentro do padrão"],
                recommended_action="Verificar RADIUS, credenciais, concentrador/BNG e logs PPPoE. Checar se problema é regional.",
                responsible_team="noc",
            ))

        # Regra: Conectado mas sem navegação (PPPoE OK, sem DNS ou LAN down)
        if state.pppoe_status == "connected" and state.ipv4_address:
            if state.dns_status in ("missing", "unreachable"):
                results.append(DiagnosisResult(
                    problem_code="no_dns",
                    problem_label="Cliente conectado mas sem DNS",
                    severity="warn",
                    confidence=80,
                    evidences=[f"PPPoE conectado, IP {state.ipv4_address}", f"DNS status: {state.dns_status}"],
                    recommended_action="Verificar DNS entregue via DHCP/RA. Testar 1.1.1.1 e resolver interno.",
                    responsible_team="noc",
                ))
            if state.lan_status == "down":
                results.append(DiagnosisResult(
                    problem_code="lan_disconnected",
                    problem_label="Porta LAN desconectada",
                    severity="warn",
                    confidence=90,
                    evidences=["Status LAN = down", "PPPoE pode estar conectado"],
                    recommended_action="Orientar cliente a verificar cabo de rede. Se bridge, verificar roteador.",
                    responsible_team="support",
                ))

        # Regra: IPv6 sem prefixo
        if state.ipv4_address and state.ipv6_status in ("no_prefix", "disabled"):
            results.append(DiagnosisResult(
                problem_code="ipv6_no_prefix",
                problem_label="IPv6 sem prefixo (PD)",
                severity="warn",
                confidence=78,
                evidences=["IPv4 ativo", f"IPv6 status: {state.ipv6_status}"],
                counter_evidences=["IPv6 pode estar desabilitado intencionalmente no plano"] ,
                recommended_action="Verificar DHCPv6-PD no BNG, rota IPv6 e configuração da ONT.",
                responsible_team="noc",
            ))

        # Regra: Wi-Fi sobrecarregado
        if state.wifi_clients_count >= settings.wifi_clients_crit:
            results.append(DiagnosisResult(
                problem_code="wifi_overloaded",
                problem_label="Wi-Fi com muitos clientes",
                severity="warn",
                confidence=70,
                evidences=[f"{state.wifi_clients_count} clientes Wi-Fi conectados"],
                recommended_action="Orientar separação 2.4/5GHz, reposicionamento ou roteador mesh. Visita se recorrente.",
                responsible_team="support",
            ))
        if state.wifi_signal_avg is not None and state.wifi_signal_avg < -75:
            results.append(DiagnosisResult(
                problem_code="wifi_weak_signal",
                problem_label="Wi-Fi com sinal fraco",
                severity="warn",
                confidence=72,
                evidences=[f"Sinal médio Wi-Fi: {state.wifi_signal_avg:.0f} dBm"],
                recommended_action="Orientar proximidade da ONT, canal menos congestionado, 5GHz.",
                responsible_team="support",
            ))

        # Regra: CPU/memória alta
        if state.cpu_usage and state.cpu_usage >= settings.cpu_warn_pct:
            results.append(DiagnosisResult(
                problem_code="high_cpu",
                problem_label="CPU elevada na ONT",
                severity="warn",
                confidence=75,
                evidences=[f"CPU: {state.cpu_usage:.0f}%"],
                recommended_action="Verificar firmware, reinício programado, quantidade de clientes Wi-Fi.",
                responsible_team="support",
            ))

        # Regra: Problema concentrado na PON (contexto agregado)
        pon_low_signal = ctx.get("pon_low_signal_count", 0)
        if pon_low_signal >= 3 and state.optical_rx_power and state.optical_rx_power < settings.optical_rx_warn_dbm:
            results.append(DiagnosisResult(
                problem_code="pon_optical_issue",
                problem_label="Problema concentrado na PON/CTO",
                severity="crit",
                confidence=85,
                evidences=[f"{pon_low_signal} ONTs com sinal baixo na mesma PON", f"RX local: {state.optical_rx_power:.1f} dBm"],
                recommended_action="Escalar para rede externa: verificar PON, splitter CTO, fibra tronco.",
                responsible_team="field",
            ))

        # Regra: PPPoE instável no POP
        pop_pppoe_issues = ctx.get("pop_pppoe_issue_count", 0)
        if pop_pppoe_issues >= 5 and state.pppoe_status == "disconnected":
            results.append(DiagnosisResult(
                problem_code="pop_pppoe_instability",
                problem_label="Instabilidade PPPoE regional",
                severity="crit",
                confidence=80,
                evidences=[f"{pop_pppoe_issues} falhas PPPoE no mesmo POP"],
                recommended_action="Acionar NOC: verificar BNG, RADIUS, CGNAT, conntrack.",
                responsible_team="noc",
            ))

        # Regra: Firmware desatualizado (se contexto informar)
        if ctx.get("firmware_outdated"):
            results.append(DiagnosisResult(
                problem_code="firmware_outdated",
                problem_label="Firmware desatualizado",
                severity="info",
                confidence=95,
                evidences=[f"Firmware atual: {state.firmware}", f"Recomendado: {ctx.get('firmware_recommended')}"],
                recommended_action="Agendar atualização via ACS/TR-069.",
                responsible_team="noc",
            ))

        score, breakdown = calculate_health_score(state)
        status = health_label(score)

        if not results and score >= 90:
            results.append(DiagnosisResult(
                problem_code="healthy",
                problem_label="Equipamento saudável",
                severity="info",
                confidence=90,
                evidences=["Todos os parâmetros dentro do padrão"],
                recommended_action="Nenhuma ação necessária.",
                responsible_team="support",
            ))

        return results, score, status, breakdown