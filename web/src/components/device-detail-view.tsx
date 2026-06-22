"use client";

import { useCallback, useEffect, useState } from "react";
import { Users, Wrench, Router, Clock, Globe, Wifi, Network, RefreshCw, Loader2, Smartphone, WifiOff } from "lucide-react";
import { StatusBadge, HealthScoreRing } from "@/components/status-badge";
import { DeviceRemoteActions } from "@/components/device-remote-actions";
import { DeviceConfigProfile } from "@/components/device-config-profile";
import { DeviceDiagnosticsDashboard } from "@/components/device-diagnostics-dashboard";
import { DeviceHardwareView } from "@/components/device-hardware-view";
import { StitchTopBar } from "@/components/stitch/top-bar";
import { PageContainer } from "@/components/page-container";
import { fetchAuthAPI } from "@/lib/auth";
import { cn } from "@/lib/utils";
import type { DeviceDetail } from "@/lib/types";

type Tab = "resumo" | "equipamento" | "diagnosticos" | "conectividade" | "cliente";

export function DeviceDetailView({ id }: { id: string }) {
  const [data, setData] = useState<DeviceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("diagnosticos");

  const loadData = useCallback(async () => {
    try {
      const detail = await fetchAuthAPI<DeviceDetail>(`/devices/${id}`);
      setData(detail);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao carregar");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    setLoading(true);
    loadData();
  }, [loadData]);

  useEffect(() => {
    if (tab === "conectividade" || tab === "equipamento") loadData();
  }, [tab, loadData]);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-10 w-10 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
      </div>
    );
  }

  if (error) return <p className="text-crit">{error}</p>;
  if (!data) return <p>Equipamento não encontrado</p>;

  const { device, snapshot, snapshot_at, data_stale, diagnoses, events } = data;
  const isStale = data_stale ?? !device.is_online;
  const lastReadLabel = snapshot_at
    ? new Date(snapshot_at).toLocaleString("pt-BR")
    : device.last_inform_at
      ? new Date(device.last_inform_at).toLocaleString("pt-BR")
      : null;
  const wifiClients = snapshot?.wifi_clients ?? [];
  const connectedCount = Math.max(snapshot?.wifi_clients_count ?? 0, wifiClients.length);
  const teamLabel: Record<string, string> = { field: "Campo", noc: "NOC", support: "Suporte", upstream: "Upstream" };

  const tabs: { id: Tab; label: string }[] = [
    { id: "resumo", label: "Resumo" },
    { id: "equipamento", label: "Equipamento" },
    { id: "conectividade", label: "Conectividade" },
    { id: "diagnosticos", label: "Diagnósticos" },
    { id: "cliente", label: "Cliente" },
  ];

  return (
    <PageContainer className="space-y-5">
      <StitchTopBar
        breadcrumb={[
          { label: "Início", href: "/" },
          { label: "Dispositivos", href: "/devices" },
          { label: device.serial_number },
        ]}
      />

      {isStale && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
          <WifiOff className="mr-2 inline h-4 w-4" />
          <strong>ONT offline</strong>
          {lastReadLabel ? (
            <> — métricas abaixo são da última leitura em {lastReadLabel}, não tempo real.</>
          ) : (
            <> — sem leitura recente do TR-069.</>
          )}
        </div>
      )}

      {/* Device header — Stitch style */}
      <div className="stitch-card overflow-hidden">
        <div className="border-b border-white/[0.06] bg-gradient-to-r from-violet-600/8 via-transparent to-cyan-600/5 px-5 py-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className={cn(
                "flex h-12 w-12 items-center justify-center rounded-xl ring-1",
                device.is_online
                  ? "bg-emerald-500/15 ring-emerald-500/25"
                  : "bg-rose-500/15 ring-rose-500/25",
              )}>
                <Router className={cn("h-6 w-6", device.is_online ? "text-emerald-300" : "text-rose-300")} />
              </div>
              <div>
                <h1 className="text-lg font-semibold">{device.manufacturer} {device.model}</h1>
                <p className="font-mono text-sm text-muted-foreground">{device.serial_number}</p>
                <div className="mt-1.5 flex flex-wrap gap-2 text-xs">
                  {snapshot?.ipv4_address && (
                    <span className="inline-flex items-center gap-1 rounded-lg bg-white/[0.04] px-2 py-0.5 font-mono">
                      <Globe className="h-3 w-3 text-cyan-400" />{snapshot.ipv4_address}
                    </span>
                  )}
                  {snapshot?.uptime_seconds != null && (
                    <span className="inline-flex items-center gap-1 rounded-lg bg-white/[0.04] px-2 py-0.5">
                      <Clock className="h-3 w-3" />{Math.floor(snapshot.uptime_seconds / 3600)}h
                    </span>
                  )}
                  <span className="text-muted-foreground">{device.firmware}</span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <StatusBadge status={device.is_online ? "online" : "offline"} />
              <div className="text-right text-xs text-muted-foreground hidden sm:block">
                <p>Health</p>
              </div>
              <HealthScoreRing score={device.health_score} />
              <StatusBadge status={device.health_status} />
            </div>
          </div>
        </div>

        <div className="flex gap-1 px-5 py-2.5 border-b border-white/[0.04]">
          {tabs.map((t) => (
            <button key={t.id} onClick={() => setTab(t.id)} className={cn("stitch-tab", tab === t.id && "stitch-tab-active")}>
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {tab === "equipamento" && (
        <DeviceHardwareView
          deviceId={device.id}
          serial={device.serial_number}
          isOnline={device.is_online}
          snapshot={snapshot}
        />
      )}

      {tab === "diagnosticos" && (
        <>
          <DeviceRemoteActions deviceId={device.id} serial={device.serial_number} />
          <DeviceConfigProfile deviceId={device.id} serial={device.serial_number} />
          <DeviceDiagnosticsDashboard deviceId={device.id} snapshot={snapshot} isOnline={device.is_online} />
        </>
      )}

      {tab === "resumo" && (
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="stitch-card p-5">
            <h2 className="text-sm font-semibold mb-4">Informações do dispositivo</h2>
            <dl className="space-y-3 text-sm">
              <div className="flex justify-between"><dt className="text-muted-foreground">Serial</dt><dd className="font-mono">{device.serial_number}</dd></div>
              <div className="flex justify-between"><dt className="text-muted-foreground">Firmware</dt><dd>{device.firmware || "—"}</dd></div>
              <div className="flex justify-between"><dt className="text-muted-foreground">Uptime</dt><dd>{snapshot?.uptime_seconds ? `${Math.floor(snapshot.uptime_seconds / 3600)}h` : "—"}</dd></div>
              <div className="flex justify-between"><dt className="text-muted-foreground">RX óptico</dt><dd>{snapshot?.optical_rx_power != null ? `${snapshot.optical_rx_power} dBm` : "—"}</dd></div>
            </dl>
          </div>

          <div className="stitch-card p-5">
            <h2 className="text-sm font-semibold mb-4 flex items-center gap-2"><Network className="h-4 w-4" /> Interfaces WAN</h2>
            <div className="space-y-2">
              <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 flex justify-between items-center">
                <div>
                  <p className="font-mono text-sm">{snapshot?.ipv4_address || "—"}</p>
                  <p className="text-xs text-muted-foreground">Endereço IP</p>
                </div>
                <StatusBadge status={snapshot?.pppoe_status === "connected" ? "connected" : "crit"} />
              </div>
              <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
                <p className="text-xs text-muted-foreground">PPPoE</p>
                <p className="font-mono text-sm mt-0.5">{device.customer?.pppoe_login || "—"}</p>
              </div>
              <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
                <p className="text-xs text-muted-foreground">IPv6</p>
                <p className="text-sm mt-0.5">{snapshot?.ipv6_prefix || "Desabilitado"}</p>
              </div>
            </div>
          </div>

          <div className="stitch-card p-5 lg:col-span-2">
            <div className="flex items-center gap-2 mb-4">
              <Wrench className="h-4 w-4 text-rose-300" />
              <h2 className="text-sm font-semibold">Diagnóstico automático</h2>
            </div>
            {diagnoses.length === 0 ? (
              <p className="text-sm text-muted-foreground">Nenhum problema detectado</p>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                {diagnoses.map((d, i) => (
                  <div key={i} className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
                    <div className="flex justify-between gap-2">
                      <p className="font-medium text-sm">{d.problem_label}</p>
                      <StatusBadge status={d.severity} />
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">{d.recommended_action}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="stitch-card p-5 lg:col-span-2">
            <h2 className="text-sm font-semibold mb-4">Eventos</h2>
            <div className="space-y-2">
              {events.map((e, i) => (
                <div key={i} className="flex gap-3 rounded-xl border-l-2 border-violet-500/40 bg-white/[0.02] pl-4 py-2">
                  <div className="flex-1">
                    <p className="text-sm font-medium">{e.title}</p>
                    <p className="text-xs text-muted-foreground">{e.description}</p>
                  </div>
                  <StatusBadge status={e.severity} />
                </div>
              ))}
              {events.length === 0 && <p className="text-sm text-muted-foreground">Nenhum evento</p>}
            </div>
          </div>
        </div>
      )}

      {tab === "conectividade" && (
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="stitch-card p-5">
            <div className="mb-3 flex items-center justify-between gap-2">
              <h2 className="text-sm font-semibold">Dispositivos conectados</h2>
              <button
                type="button"
                disabled={syncing}
                onClick={async () => {
                  setSyncing(true);
                  try {
                    await fetchAuthAPI(`/devices/${device.id}/actions/sync`, { method: "POST" });
                    await loadData();
                  } finally {
                    setSyncing(false);
                  }
                }}
                className="rounded-lg p-1.5 text-muted-foreground hover:bg-white/[0.05] hover:text-foreground disabled:opacity-40"
                title="Sincronizar com GenieACS"
              >
                {syncing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              </button>
            </div>
            <p className="text-4xl font-bold">{connectedCount}</p>
            <p className="text-xs text-muted-foreground">Clientes Wi-Fi</p>
            {connectedCount === 0 ? (
              <p className="mt-4 rounded-xl border border-dashed border-white/[0.08] py-6 text-center text-xs text-muted-foreground">
                Sem dispositivos ativos — clique em sincronizar
              </p>
            ) : (
              <div className="mt-4 space-y-2">
                {wifiClients.map((c) => (
                  <div key={`${c.mac}-${c.wlan_index}`} className="rounded-xl border border-white/[0.06] bg-white/[0.02] px-3 py-2.5">
                    <div className="flex items-center gap-2">
                      <Smartphone className="h-4 w-4 shrink-0 text-violet-300" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">{c.name || c.mac}</p>
                        <p className="font-mono text-[10px] text-muted-foreground">{c.mac}</p>
                      </div>
                      {c.rssi != null && (
                        <span className="shrink-0 text-xs font-mono text-emerald-300">{c.rssi} dBm</span>
                      )}
                    </div>
                    <p className="mt-1 text-[10px] text-muted-foreground">
                      {c.ssid ?? "Wi-Fi"}{c.ip ? ` · ${c.ip}` : ""}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="stitch-card p-5 lg:col-span-2">
            <h2 className="text-sm font-semibold mb-4 flex items-center gap-2"><Wifi className="h-4 w-4" /> Redes Wi-Fi</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              {snapshot?.wifi_networks?.length ? snapshot.wifi_networks.map((n) => (
                <div key={n.index} className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
                  <div className="flex items-center gap-2">
                    <span className={`h-2 w-2 rounded-full ${n.clients > 0 ? "bg-emerald-400" : "bg-white/20"}`} />
                    <p className="font-medium text-sm">{n.ssid}</p>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">Canal {n.channel ?? "—"} · {n.band}</p>
                  <p className={`text-xs mt-1 ${n.clients > 0 ? "text-emerald-400" : "text-muted-foreground"}`}>
                    {n.clients} cliente(s)
                  </p>
                </div>
              )) : <p className="text-sm text-muted-foreground">Sincronize a ONT para ver as redes Wi-Fi</p>}
            </div>
          </div>
        </div>
      )}

      {tab === "cliente" && (
        <div className="stitch-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <Users className="h-4 w-4" />
            <h2 className="text-sm font-semibold">Cliente vinculado</h2>
          </div>
          {device.customer ? (
            <dl className="grid gap-3 sm:grid-cols-3 text-sm">
              <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
                <dt className="text-xs text-muted-foreground uppercase">Nome</dt>
                <dd className="font-medium mt-1">{device.customer.name}</dd>
              </div>
              <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
                <dt className="text-xs text-muted-foreground uppercase">PPPoE</dt>
                <dd className="font-mono mt-1">{device.customer.pppoe_login}</dd>
              </div>
              <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
                <dt className="text-xs text-muted-foreground uppercase">Bairro</dt>
                <dd className="mt-1">{device.customer.neighborhood}</dd>
              </div>
            </dl>
          ) : (
            <p className="text-sm text-muted-foreground">Sem cliente vinculado</p>
          )}
        </div>
      )}
    </PageContainer>
  );
}