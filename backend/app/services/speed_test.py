"""Configuração de testes de velocidade — Minha Conexão / OoklaServer."""

from typing import Any, Optional
import httpx

from ..config import settings

MC_API = "https://api.minhaconexao.com.br/v1"


def speed_test_config() -> dict[str, str]:
    return {
        "server_name": settings.speed_test_server_name,
        "server_city": settings.speed_test_server_city,
        "server_host": settings.speed_test_server_host,
        "download_url": settings.speed_test_download_url,
        "upload_url": settings.speed_test_upload_url,
        "provider": "minhaconexao",
    }


async def resolve_mc_server(lat: float, lng: float) -> Optional[dict[str, Any]]:
    """Busca servidor Minha Conexão mais próximo (API pública)."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{MC_API}/server/search", params={"lat": lat, "lng": lng})
            if r.status_code != 200:
                return None
            servers = r.json()
            if not servers:
                return None
            top = servers[0]
            host = str(top.get("host", ""))
            http_host = host.replace(":9090", ":8080") if ":9090" in host else host
            return {
                "id": top.get("id"),
                "name": top.get("displayName") or top.get("name"),
                "city": top.get("city"),
                "state": top.get("state"),
                "host_ws": host,
                "host_http": http_host,
                "download_url": f"http://{http_host}/speedtest/random3500x3500.jpg",
            }
    except Exception:
        return None