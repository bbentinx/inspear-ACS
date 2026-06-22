"""Configuração TR-069/CWMP para provisionamento manual na ONT."""

from ..config import settings


def tr069_ont_config() -> dict:
    """Valores para preencher na ONT Huawei (EG8145V5) — System Management → TR-069."""
    cwmp = settings.genieacs_cwmp_url.rstrip("/")
    return {
        "manufacturer": "Huawei",
        "models": ["EG8145V5", "EG8145X5", "HG8245"],
        "menu_path": "System Management → TR-069",
        "acs": {
            "url": cwmp,
            "username": settings.genieacs_acs_user,
            "password": settings.genieacs_acs_password,
        },
        "connection_request": {
            "username": settings.genieacs_cr_user,
            "password": settings.genieacs_cr_password,
        },
        "options": {
            "enable_acs_management": True,
            "enable_periodic_informing": True,
            "informing_interval_seconds": 300,
            "informing_interval_lab_seconds": 30,
        },
        "ports": {
            "cwmp": 7547,
            "genieacs_ui": 3001,
            "inspear_panel": 3000,
            "inspear_api": 8000,
        },
        "urls": {
            "cwmp": cwmp,
            "public_api": settings.public_api_base_url.rstrip("/"),
            "webhook": f"{settings.public_api_base_url.rstrip('/')}/api/v1/acs/genieacs/webhook",
            "vendor_config_pattern": f"{settings.public_api_base_url.rstrip('/')}/api/v1/acs/vendor-file/{{serial}}.xml",
        },
        "lab_profile": {
            "wan_vlan": 10,
            "wifi_24_ssid": "Lab-2.4G",
            "wifi_5_ssid": "Lab-5G",
            "city": "Fernandópolis",
        },
        "notes": [
            "Todos os campos ACS e Connection Request são obrigatórios na Huawei.",
            "Após reset físico, reaponte ACS URL na interface local (192.168.100.1) ou use restore remoto.",
            "Connection Request exige porta 7547 acessível da ONT até o servidor.",
            "Inform interval 30s acelera testes em bancada; 300s é o padrão em produção.",
        ],
    }