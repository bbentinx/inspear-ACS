export interface DashboardStats {
  total_devices: number;
  online_devices: number;
  offline_devices: number;
  critical_devices: number;
  degraded_devices: number;
  diagnoses_24h: number;
  alerts_open: number;
  by_pop: ImpactGroup[];
  by_model: ImpactGroup[];
  recent_diagnoses: RecentDiagnosis[];
}

export interface ImpactGroup {
  type: string;
  name: string;
  affected: number;
  critical: number;
  degraded: number;
  diagnosis?: string;
}

export interface RecentDiagnosis {
  id?: number;
  problem_label: string;
  severity: string;
  device_id?: string;
  device_serial?: string;
  customer_name?: string;
  responsible_team?: string;
  confidence?: number;
}

export interface DeviceListItem {
  id: string;
  serial_number: string;
  manufacturer: string;
  model: string;
  firmware?: string | null;
  is_online: boolean;
  health_score: number;
  health_status: string;
  customer_name?: string | null;
  pop_id?: number | null;
  last_inform_at?: string | null;
}

export interface DeviceCustomer {
  id: string;
  name: string;
  pppoe_login?: string | null;
  neighborhood?: string | null;
}

export interface DeviceSnapshot {
  optical_rx_power?: number | null;
  optical_tx_power?: number | null;
  optical_temperature?: number | null;
  uptime_seconds?: number | null;
  pppoe_status?: string | null;
  pppoe_username?: string | null;
  ipv4_address?: string | null;
  ipv6_prefix?: string | null;
  ipv6_status?: string | null;
  dns_servers?: string[];
  dns_status?: string | null;
  lan_status?: string | null;
  lan_speed_mbps?: number | null;
  wifi_ssid?: string | null;
  wifi_clients_count?: number | null;
  wifi_signal_avg?: number | null;
  wifi_networks?: { index: number; ssid: string; band: string; clients: number; channel?: number | null }[];
  wifi_clients?: {
    mac?: string | null;
    rssi?: number | null;
    wlan_index: number;
    ssid?: string | null;
    name?: string | null;
    ip?: string | null;
    detail_unavailable?: boolean;
  }[];
  cpu_usage?: number | null;
  memory_usage?: number | null;
  reboot_count_24h?: number | null;
}

export interface DeviceDiagnosis {
  problem_code: string;
  problem_label: string;
  severity: string;
  confidence: number;
  evidences: string[];
  counter_evidences?: string[];
  recommended_action: string;
  responsible_team: string;
}

export interface DeviceEvent {
  type: string;
  severity: string;
  title: string;
  description?: string | null;
  at: string;
}

export interface DeviceDetail {
  device: {
    id: string;
    serial_number: string;
    manufacturer: string;
    model: string;
    firmware?: string | null;
    is_online: boolean;
    health_score: number;
    health_status: string;
    last_inform_at?: string | null;
    mgmt_ip?: string | null;
    pop_id?: number | null;
    olt_id?: number | null;
    pon_id?: number | null;
    onu_id?: number | null;
    customer?: DeviceCustomer | null;
  };
  snapshot: DeviceSnapshot | null;
  snapshot_at?: string | null;
  data_stale?: boolean;
  diagnoses: DeviceDiagnosis[];
  events: DeviceEvent[];
}

export interface TimelineItem {
  at: string;
  type: string;
  title: string;
  severity: string;
  description?: string | null;
  device_serial?: string | null;
}