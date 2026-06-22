"""Alertas Telegram."""

import httpx
from ..config import settings


async def send_telegram_alert(message: str) -> bool:
    if not settings.alerts_enabled or not settings.telegram_bot_token or not settings.telegram_chat_id:
        return False
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json={
                "chat_id": settings.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML",
            })
            return r.status_code == 200
    except Exception:
        return False


def format_alert(device_serial: str, diagnosis_label: str, severity: str, action: str, customer: str = "") -> str:
    emoji = {"crit": "🔴", "warn": "🟡", "info": "🔵"}.get(severity, "⚪")
    lines = [
        f"{emoji} <b>Inspear ACS — {severity.upper()}</b>",
        f"<b>ONT:</b> {device_serial}",
    ]
    if customer:
        lines.append(f"<b>Cliente:</b> {customer}")
    lines.extend([
        f"<b>Problema:</b> {diagnosis_label}",
        f"<b>Ação:</b> {action}",
    ])
    return "\n".join(lines)