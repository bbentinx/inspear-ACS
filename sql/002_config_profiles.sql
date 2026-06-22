-- Perfil de configuração desejada por ONT (restore remoto pós-reset)

CREATE TABLE IF NOT EXISTS device_config_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID UNIQUE NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    serial_number VARCHAR(64) NOT NULL,
    acs_url TEXT,
    acs_username VARCHAR(128),
    acs_password VARCHAR(128),
    cr_username VARCHAR(128),
    cr_password VARCHAR(128),
    periodic_inform_interval INTEGER DEFAULT 300,
    pppoe_username VARCHAR(128),
    pppoe_password VARCHAR(256),
    wan_vlan INTEGER,
    wifi_24_ssid VARCHAR(64),
    wifi_24_password VARCHAR(128),
    wifi_5_ssid VARCHAR(64),
    wifi_5_password VARCHAR(128),
    auto_restore_enabled BOOLEAN DEFAULT TRUE,
    source VARCHAR(32) DEFAULT 'auto',
    last_captured_at TIMESTAMPTZ,
    last_applied_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_config_profiles_serial ON device_config_profiles(serial_number);