-- Inspear ACS Inteligente — Schema v1

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Topologia rede
CREATE TABLE pops (
    id SERIAL PRIMARY KEY,
    code VARCHAR(32) UNIQUE NOT NULL,
    name VARCHAR(128) NOT NULL,
    city VARCHAR(64),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE olts (
    id SERIAL PRIMARY KEY,
    pop_id INTEGER REFERENCES pops(id),
    name VARCHAR(64) NOT NULL,
    vendor VARCHAR(64),
    mgmt_ip INET,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE pons (
    id SERIAL PRIMARY KEY,
    olt_id INTEGER NOT NULL REFERENCES olts(id),
    slot INTEGER,
    pon_port VARCHAR(16) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(olt_id, slot, pon_port)
);

CREATE TABLE ctos (
    id SERIAL PRIMARY KEY,
    pon_id INTEGER REFERENCES pons(id),
    code VARCHAR(32) NOT NULL,
    neighborhood VARCHAR(128),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE pppoe_concentrators (
    id SERIAL PRIMARY KEY,
    pop_id INTEGER REFERENCES pops(id),
    name VARCHAR(64) NOT NULL,
    vendor VARCHAR(64),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Clientes
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_code VARCHAR(64) UNIQUE,
    name VARCHAR(256) NOT NULL,
    document VARCHAR(32),
    phone VARCHAR(32),
    email VARCHAR(256),
    address TEXT,
    neighborhood VARCHAR(128),
    pop_id INTEGER REFERENCES pops(id),
    pppoe_login VARCHAR(128) UNIQUE,
    status VARCHAR(32) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Equipamentos (ONT/roteador)
CREATE TABLE devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    serial_number VARCHAR(64) UNIQUE NOT NULL,
    mac_wan VARCHAR(17),
    manufacturer VARCHAR(64) NOT NULL,
    model VARCHAR(128) NOT NULL,
    firmware VARCHAR(64),
    device_type VARCHAR(32) DEFAULT 'ont', -- ont, router, ont_router
    customer_id UUID REFERENCES customers(id),
    -- Topologia
    pop_id INTEGER REFERENCES pops(id),
    olt_id INTEGER REFERENCES olts(id),
    pon_id INTEGER REFERENCES pons(id),
    onu_id INTEGER,
    cto_id INTEGER REFERENCES ctos(id),
    concentrator_id INTEGER REFERENCES pppoe_concentrators(id),
    -- Estado ACS
    is_online BOOLEAN DEFAULT FALSE,
    mgmt_ip INET,
    last_inform_at TIMESTAMPTZ,
    last_boot_at TIMESTAMPTZ,
    uptime_seconds BIGINT DEFAULT 0,
    health_score SMALLINT DEFAULT 100,
    health_status VARCHAR(16) DEFAULT 'healthy', -- healthy, attention, degraded, critical
    -- TR-069
    cwmp_connection_request_url TEXT,
    cwmp_last_session TIMESTAMPTZ,
    adapter_type VARCHAR(32) DEFAULT 'generic', -- huawei, zte, fiberhome, generic
    raw_capabilities JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_devices_customer ON devices(customer_id);
CREATE INDEX idx_devices_online ON devices(is_online);
CREATE INDEX idx_devices_health ON devices(health_status);
CREATE INDEX idx_devices_pon ON devices(pon_id);
CREATE INDEX idx_devices_pop ON devices(pop_id);

-- Inform TR-069 / ingestão API (snapshot normalizado)
CREATE TABLE device_snapshots (
    id BIGSERIAL PRIMARY KEY,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    source VARCHAR(32) NOT NULL DEFAULT 'api', -- api, cwmp, manual
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Óptico
    optical_rx_power REAL,
    optical_tx_power REAL,
    optical_temperature REAL,
    optical_voltage REAL,
    optical_bias_current REAL,
    -- WAN / PPPoE
    wan_status VARCHAR(32),
    pppoe_status VARCHAR(32),
    pppoe_username VARCHAR(128),
    ipv4_address INET,
    ipv6_prefix VARCHAR(64),
    ipv6_status VARCHAR(32),
    dns_servers TEXT[],
    dns_status VARCHAR(32),
    -- LAN
    lan_status VARCHAR(32),
    lan_speed_mbps INTEGER,
    lan_errors INTEGER DEFAULT 0,
    -- Wi-Fi
    wifi_ssid VARCHAR(64),
    wifi_channel INTEGER,
    wifi_clients_count INTEGER DEFAULT 0,
    wifi_signal_avg REAL,
    -- Sistema
    cpu_usage REAL,
    memory_usage REAL,
    reboot_count_24h INTEGER DEFAULT 0,
    last_reboot_reason VARCHAR(128),
    uptime_seconds BIGINT,
    last_error TEXT,
    -- Normalizado completo
    normalized JSONB NOT NULL DEFAULT '{}',
    raw_payload JSONB DEFAULT '{}'
);

CREATE INDEX idx_snapshots_device_time ON device_snapshots(device_id, received_at DESC);

-- Eventos (reboot, offline, alarme óptico, etc.)
CREATE TABLE device_events (
    id BIGSERIAL PRIMARY KEY,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    event_type VARCHAR(64) NOT NULL,
    severity VARCHAR(16) NOT NULL DEFAULT 'info', -- info, warn, crit
    title VARCHAR(256) NOT NULL,
    description TEXT,
    payload JSONB DEFAULT '{}',
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_events_device_time ON device_events(device_id, occurred_at DESC);
CREATE INDEX idx_events_type ON device_events(event_type, occurred_at DESC);

-- Diagnósticos automáticos
CREATE TABLE diagnoses (
    id BIGSERIAL PRIMARY KEY,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    snapshot_id BIGINT REFERENCES device_snapshots(id),
    problem_code VARCHAR(64) NOT NULL,
    problem_label VARCHAR(256) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    confidence REAL NOT NULL,
    evidences JSONB NOT NULL DEFAULT '[]',
    counter_evidences JSONB DEFAULT '[]',
    recommended_action TEXT NOT NULL,
    responsible_team VARCHAR(32) NOT NULL, -- support, noc, field, upstream
    health_score SMALLINT,
    is_active BOOLEAN DEFAULT TRUE,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_diagnoses_active ON diagnoses(device_id, is_active, created_at DESC);

-- Alertas
CREATE TABLE alerts (
    id BIGSERIAL PRIMARY KEY,
    device_id UUID REFERENCES devices(id),
    diagnosis_id BIGINT REFERENCES diagnoses(id),
    alert_type VARCHAR(64) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    message TEXT NOT NULL,
    scope_type VARCHAR(32), -- device, pon, olt, pop, model
    scope_id VARCHAR(64),
    fired_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    notified_telegram BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_alerts_open ON alerts(fired_at DESC) WHERE resolved_at IS NULL;

-- Agregações de problema (PON/POP/modelo)
CREATE TABLE problem_aggregations (
    id BIGSERIAL PRIMARY KEY,
    scope_type VARCHAR(32) NOT NULL,
    scope_key VARCHAR(128) NOT NULL,
    problem_code VARCHAR(64) NOT NULL,
    affected_devices INTEGER DEFAULT 0,
    severity VARCHAR(16) NOT NULL,
    first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    details JSONB DEFAULT '{}'
);

-- Usuários NOC
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(256) UNIQUE NOT NULL,
    name VARCHAR(128) NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    role VARCHAR(32) DEFAULT 'noc', -- admin, noc, support, field
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seeds MVP
INSERT INTO pops (code, name, city) VALUES
    ('centro', 'POP Centro', 'Sua Cidade'),
    ('norte', 'POP Norte', 'Sua Cidade');

INSERT INTO olts (pop_id, name, vendor) VALUES
    (1, 'OLT-03', 'Huawei'),
    (1, 'OLT-02', 'Huawei'),
    (2, 'OLT-01', 'ZTE');

INSERT INTO pons (id, olt_id, slot, pon_port) VALUES
    (1, 1, 0, '0/1/1'),
    (2, 3, 0, '0/2/1');
SELECT setval('pons_id_seq', (SELECT COALESCE(MAX(id), 1) FROM pons));

INSERT INTO pppoe_concentrators (pop_id, name, vendor) VALUES
    (1, 'BNG-02', 'MikroTik'),
    (2, 'BNG-01', 'Accel-PPP');