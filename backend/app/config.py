from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Inspear ACS"
    app_env: str = "development"
    secret_key: str = "change-me"
    database_url: str = "postgresql+asyncpg://inspear:changeme@localhost:5432/inspear"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me-jwt"
    jwt_expire_minutes: int = 480
    auth_enabled: bool = True
    admin_email: str = "admin@inspear.local"
    admin_password: str = "admin123"
    inspear_api_key: str = "inspear-dev-key"
    genieacs_nbi_url: str = "http://genieacs-nbi:7557"
    genieacs_cwmp_url: str = "http://localhost:7547"
    genieacs_acs_user: str = "inspear"
    genieacs_acs_password: str = "inspear123"
    genieacs_cr_user: str = "inspear-cr"
    genieacs_cr_password: str = "inspear123"
    genieacs_sync_enabled: bool = True
    genieacs_sync_interval_seconds: int = 300
    auto_capture_config_profile: bool = True
    offline_threshold_minutes: int = 15
    allow_simulated_actions: bool = True
    firmware_server_url: str = "http://inspear-api:8000/firmware"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    alerts_enabled: bool = True
    optical_rx_warn_dbm: float = -25.0
    optical_rx_crit_dbm: float = -27.0
    reboot_warn_24h: int = 3
    reboot_crit_24h: int = 6
    wifi_clients_warn: int = 15
    wifi_clients_crit: int = 25
    cpu_warn_pct: float = 80.0
    memory_warn_pct: float = 85.0
    speed_test_server_name: str = "core Lab Fer"
    speed_test_server_city: str = "Fernandópolis"
    speed_test_server_host: str = "localhost:8000"
    speed_test_download_url: str = (
        "http://localhost:8000/examples/speedtest/100mb.bin"
    )
    speed_test_upload_url: str = "http://speedtest.tele2.net/upload.php"
    public_api_base_url: str = "http://localhost:8000"

    class Config:
        env_file = ".env"


settings = Settings()