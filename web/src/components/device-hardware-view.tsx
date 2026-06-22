"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Globe, Wifi, RotateCcw, Smartphone, Server,
  Loader2, RefreshCw, Plus, CheckCircle2, AlertCircle, Lock, LockOpen,
} from "lucide-react";
import { fetchAuthAPI } from "@/lib/auth";
import { cn } from "@/lib/utils";
import type { DeviceSnapshot } from "@/lib/types";

type Zone = "internet" | "wifi" | "lan1" | "lan2" | "lan3" | "lan4" | "usb" | "reset" | "forward" | "clients";

interface LanPort { index: number; status: string; enabled: boolean; connected: boolean }
interface WifiNet {
  index: number; ssid: string; band: string; clients: number; enabled?: boolean;
  beacon_type?: string; open?: boolean; security_label?: string;
}
interface PortForward {
  index: number; enabled: boolean;
  external_port: number | string; internal_port: number | string;
  internal_client: string; protocol: string; description?: string;
}
interface HardwareData {
  supported: boolean; model: string; device_online?: boolean;
  internet: { connected: boolean; ipv4?: string; vlan?: number; optical_rx_dbm?: number; pppoe_status?: string };
  wifi: WifiNet[];
  wifi_clients: Array<{ mac: string; name?: string; ssid?: string; ip?: string; rssi?: number }>;
  wifi_clients_count: number;
  lan_ports: LanPort[];
  port_forwards: PortForward[];
}

interface Props {
  deviceId: string;
  serial: string;
  isOnline: boolean;
  snapshot: DeviceSnapshot | null;
}

const ZONE_LABELS: Record<Zone, string> = {
  internet: "Internet / WAN", wifi: "Wi-Fi",
  lan1: "Porta LAN 1", lan2: "Porta LAN 2", lan3: "Porta LAN 3", lan4: "Porta LAN 4",
  usb: "USB", reset: "Reset", forward: "Redirecionamento de porta", clients: "Dispositivos conectados",
};

const CX = 320;
const CY = 168;
const VB_W = 640;
const VB_H = 360;

export function DeviceHardwareView({ deviceId, isOnline, snapshot }: Props) {
  const [hw, setHw] = useState<HardwareData | null>(null);
  const [zone, setZone] = useState<Zone>("internet");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<{ type: "ok" | "err" | "wait"; text: string } | null>(null);

  const [wifiForm, setWifiForm] = useState({ wlan_index: 1, ssid: "", password: "", open: false });
  const [pfForm, setPfForm] = useState({
    external_port: "8080", internal_port: "8080",
    internal_client: "192.168.1.100", protocol: "TCP", description: "",
  });

  const load = useCallback(async () => {
    try {
      const data = await fetchAuthAPI<HardwareData>(`/devices/${deviceId}/hardware`);
      setHw(data);
      const active = data.wifi.find((w) => w.index === wifiForm.wlan_index);
      if (active) {
        setWifiForm((f) => ({
          ...f,
          ssid: active.ssid || f.ssid,
          open: active.open ?? false,
        }));
      }
    } catch (e) {
      setStatus({ type: "err", text: e instanceof Error ? e.message : "Falha ao carregar" });
    } finally {
      setLoading(false);
    }
  }, [deviceId, wifiForm.wlan_index]);

  useEffect(() => { setLoading(true); load(); }, [load]);

  async function pollUntilChange(
    check: (data: HardwareData) => boolean,
    label: string,
    attempts = 14,
    intervalSec = 5,
  ) {
    for (let i = 0; i < attempts; i++) {
      setStatus({ type: "wait", text: `${label} (~${(i + 1) * intervalSec}s)...` });
      await new Promise((r) => setTimeout(r, intervalSec * 1000));
      try {
        await fetchAuthAPI(`/devices/${deviceId}/actions/sync`, { method: "POST" });
      } catch { /* sync opcional */ }
      try {
        const data = await fetchAuthAPI<HardwareData>(`/devices/${deviceId}/hardware`);
        setHw(data);
        if (check(data)) return true;
      } catch { /* retry */ }
    }
    return false;
  }

  async function applyWifi() {
    if (!wifiForm.ssid && !wifiForm.open && !wifiForm.password) {
      setStatus({ type: "err", text: "Informe SSID ou marque rede aberta" });
      return;
    }
    setSaving(true);
    setStatus(null);
    const expectOpen = wifiForm.open;
    const wlanIdx = wifiForm.wlan_index;
    const expectSsid = wifiForm.ssid;
    try {
      const r = await fetchAuthAPI<{ message: string }>(`/devices/${deviceId}/actions/wifi`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          wlan_index: wlanIdx,
          ssid: wifiForm.ssid || undefined,
          password: wifiForm.open ? undefined : (wifiForm.password || undefined),
          open_network: wifiForm.open,
        }),
      });
      setStatus({ type: "wait", text: r.message });
      const ok = await pollUntilChange(
        (data) => {
          const net = data.wifi.find((w) => w.index === wlanIdx);
          if (!net) return false;
          const ssidOk = !expectSsid || net.ssid === expectSsid;
          const openOk = expectOpen ? !!net.open : true;
          return ssidOk && openOk;
        },
        "Aguardando ONT aplicar Wi-Fi",
      );
      setStatus({
        type: ok ? "ok" : "err",
        text: ok
          ? (expectOpen ? "Rede aberta confirmada na ONT" : "Wi-Fi atualizado na ONT")
          : "Comando enviado — ONT offline ou aguardando próximo Inform (30s)",
      });
    } catch (e) {
      setStatus({ type: "err", text: e instanceof Error ? e.message : "Erro Wi-Fi" });
    } finally {
      setSaving(false);
    }
  }

  async function applyPortForward() {
    setSaving(true);
    setStatus(null);
    try {
      const r = await fetchAuthAPI<{ message: string }>(`/devices/${deviceId}/actions/port-forward`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          external_port: Number(pfForm.external_port),
          internal_port: Number(pfForm.internal_port),
          internal_client: pfForm.internal_client,
          protocol: pfForm.protocol,
          description: pfForm.description,
        }),
      });
      setStatus({ type: "wait", text: r.message });
      const ok = await pollUntilChange(
        (data) => (data.port_forwards?.length ?? 0) > (hw?.port_forwards?.length ?? 0),
        "Aguardando redirecionamento",
        10,
        6,
      );
      setStatus({ type: ok ? "ok" : "err", text: ok ? "Redirecionamento criado" : "Enviado — aguarde ONT online" });
      setZone("forward");
    } catch (e) {
      setStatus({ type: "err", text: e instanceof Error ? e.message : "Erro redirecionamento" });
    } finally {
      setSaving(false);
    }
  }

  async function toggleForward(index: number, enabled: boolean) {
    setSaving(true);
    try {
      const r = await fetchAuthAPI<{ message: string }>(`/devices/${deviceId}/actions/port-forward/toggle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ index, enabled }),
      });
      setStatus({ type: "ok", text: r.message });
      await pollUntilChange(() => true, "Atualizando", 3, 4);
      await load();
    } catch (e) {
      setStatus({ type: "err", text: e instanceof Error ? e.message : "Erro" });
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="stitch-card flex justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
      </div>
    );
  }

  const online = hw?.device_online ?? isOnline;
  const internetOk = hw?.internet?.connected ?? snapshot?.pppoe_status === "connected";
  const wifiActive = (hw?.wifi_clients_count ?? 0) > 0;
  const lanPorts = hw?.lan_ports ?? [
    { index: 1, status: "NoLink", enabled: true, connected: false },
    { index: 2, status: "—", enabled: true, connected: false },
    { index: 3, status: "—", enabled: true, connected: false },
    { index: 4, status: "—", enabled: true, connected: false },
  ];

  const nodes: Array<{
    id: Zone; x: number; y: number; label: string; sub?: string;
    icon: React.ComponentType<{ className?: string }>;
    active: boolean; color: string;
  }> = [
    { id: "internet", x: 72, y: 72, label: "Internet", sub: internetOk ? "PPPoE" : "Off", icon: Globe, active: internetOk, color: "#34d399" },
    { id: "wifi", x: 568, y: 72, label: "Wi-Fi", sub: `${hw?.wifi_clients_count ?? 0} cli.`, icon: Wifi, active: wifiActive || (hw?.wifi?.some((w) => w.enabled) ?? false), color: "#38bdf8" },
    { id: "clients", x: 72, y: 300, label: "Celular", sub: wifiActive ? "Wi-Fi" : "—", icon: Smartphone, active: wifiActive, color: "#a78bfa" },
    { id: "forward", x: 568, y: 300, label: "Servidor", sub: `${hw?.port_forwards?.length ?? 0} regras`, icon: Server, active: (hw?.port_forwards?.length ?? 0) > 0, color: "#22d3ee" },
  ];

  const lanChipY = 252;
  const lanChipW = 44;
  const lanChipGap = 10;
  const lanStartX = CX - (lanPorts.length * lanChipW + (lanPorts.length - 1) * lanChipGap) / 2;

  function FlowLine({ x1, y1, x2, y2, active, color }: { x1: number; y1: number; x2: number; y2: number; active: boolean; color: string }) {
    return (
      <line
        x1={x1} y1={y1} x2={x2} y2={y2}
        stroke={active ? color : "#334155"}
        strokeWidth={active ? 2 : 1.5}
        strokeLinecap="round"
        opacity={active ? 0.85 : 0.3}
        className={active ? "hw-line-active" : undefined}
      />
    );
  }

  function NodeButton({
    id, x, y, label, sub, icon: Icon, active, color, size = 48,
  }: {
    id: Zone; x: number; y: number; label: string; sub?: string;
    icon: React.ComponentType<{ className?: string }>;
    active: boolean; color: string; size?: number;
  }) {
    const selected = zone === id;
    const r = size / 2;
    return (
      <g
        className="cursor-pointer"
        onClick={() => setZone(id)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && setZone(id)}
        aria-label={label}
      >
        {selected && (
          <circle cx={x} cy={y} r={r + 6} fill="none" stroke="#22d3ee" strokeWidth="1.5" opacity="0.7" />
        )}
        <circle
          cx={x} cy={y} r={r}
          fill={selected ? "rgba(34,211,238,0.14)" : "rgba(15,23,42,0.92)"}
          stroke={selected ? "#22d3ee" : active ? color : "#475569"}
          strokeWidth={selected ? 2 : active ? 1.75 : 1.25}
        />
        <foreignObject x={x - r} y={y - r} width={size} height={size} style={{ pointerEvents: "none" }}>
          <div className="flex h-full items-center justify-center" style={{ color: active ? color : "#94a3b8" }}>
            <Icon className="h-4 w-4" />
          </div>
        </foreignObject>
        <text x={x} y={y + r + 12} textAnchor="middle" fill="#e2e8f0" fontSize="9" fontWeight="600">{label}</text>
        {sub && (
          <text x={x} y={y + r + 22} textAnchor="middle" fill="#64748b" fontSize="7.5">{sub}</text>
        )}
        {active && (
          <circle cx={x + r - 4} cy={y - r + 4} r="3" fill="#34d399" />
        )}
      </g>
    );
  }

  function LanPortChip({ port, x }: { port: LanPort; x: number }) {
    const id = `lan${port.index}` as Zone;
    const selected = zone === id;
    const y = lanChipY;
    const w = lanChipW;
    const h = 26;
    return (
      <g
        className="cursor-pointer"
        onClick={() => setZone(id)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && setZone(id)}
        aria-label={`LAN ${port.index}`}
      >
        <rect
          x={x} y={y} width={w} height={h} rx={6}
          fill={selected ? "rgba(34,211,238,0.15)" : port.connected ? "rgba(52,211,153,0.12)" : "rgba(15,23,42,0.85)"}
          stroke={selected ? "#22d3ee" : port.connected ? "#34d399" : "#475569"}
          strokeWidth={selected ? 1.5 : 1}
        />
        <circle cx={x + 8} cy={y + h / 2} r="2.5" fill={port.connected ? "#34d399" : "#64748b"} />
        <text x={x + w / 2 + 4} y={y + h / 2 + 3.5} textAnchor="middle" fill={port.connected ? "#a7f3d0" : "#94a3b8"} fontSize="8" fontWeight="600">
          LAN{port.index}
        </text>
      </g>
    );
  }

  const activeWifi = hw?.wifi.find((w) => w.index === wifiForm.wlan_index);

  return (
    <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
      <div className="stitch-card relative overflow-hidden p-5 md:p-8">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_30%_20%,rgba(56,189,248,0.1),transparent_55%)]" />
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_70%_80%,rgba(52,211,153,0.06),transparent_50%)]" />
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.15]"
          style={{
            backgroundImage: "linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px)",
            backgroundSize: "28px 28px",
          }}
        />

        <div className="relative mb-4 flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold tracking-tight">Topologia EG8145V5</h2>
              <span className={cn(
                "rounded-full px-2 py-0.5 text-[10px] font-medium",
                online ? "bg-emerald-500/15 text-emerald-300" : "bg-amber-500/15 text-amber-300",
              )}>
                {online ? "ONT online" : "ONT offline"}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">Clique nos nós · pontos verdes = link ativo · animação = tráfego</p>
          </div>
          <button
            type="button"
            onClick={() => { setLoading(true); load(); }}
            className="rounded-xl border border-white/10 bg-white/5 p-2.5 hover:bg-white/10"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>

        <svg viewBox={`0 0 ${VB_W} ${VB_H}`} className="relative z-10 mx-auto w-full max-w-2xl" aria-label="Topologia ONT">
          <defs>
            <linearGradient id="ontBody" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#0ea5e9" />
              <stop offset="50%" stopColor="#0284c7" />
              <stop offset="100%" stopColor="#0369a1" />
            </linearGradient>
            <filter id="ontShadow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="4" stdDeviation="5" floodColor="#0ea5e9" floodOpacity="0.35" />
            </filter>
          </defs>

          {/* Linhas — desenhadas antes dos nós */}
          <FlowLine x1={72} y1={72} x2={CX - 70} y2={CY - 28} active={internetOk} color="#34d399" />
          <FlowLine x1={568} y1={72} x2={CX + 70} y2={CY - 28} active={wifiActive} color="#38bdf8" />
          <FlowLine x1={72} y1={300} x2={CX - 50} y2={CY + 20} active={wifiActive} color="#a78bfa" />
          <FlowLine x1={568} y1={300} x2={CX + 50} y2={CY + 20} active={(hw?.port_forwards?.length ?? 0) > 0} color="#22d3ee" />
          {lanPorts.map((p, i) => {
            const x = lanStartX + i * (lanChipW + lanChipGap) + lanChipW / 2;
            return (
              <FlowLine key={p.index} x1={x} y1={lanChipY} x2={CX + (x - CX) * 0.15} y2={CY + 34} active={p.connected} color="#60a5fa" />
            );
          })}

          {/* ONT central */}
          <g className="cursor-pointer" onClick={() => setZone("internet")} role="button" tabIndex={0}>
            <rect x={CX - 88} y={CY - 36} width={176} height={72} rx={16} fill="url(#ontBody)" filter="url(#ontShadow)" />
            <text x={CX} y={CY - 8} textAnchor="middle" fill="white" fontSize="13" fontWeight="700">EG8145V5</text>
            <text x={CX} y={CY + 8} textAnchor="middle" fill="rgba(255,255,255,0.65)" fontSize="8">Huawei GPON</text>
          </g>

          {/* Portas LAN — chips compactos abaixo da ONT */}
          {lanPorts.map((p, i) => (
            <LanPortChip key={p.index} port={p} x={lanStartX + i * (lanChipW + lanChipGap)} />
          ))}

          {/* USB / Reset — laterais, fora do corpo */}
          <g onClick={() => setZone("usb")} className="cursor-pointer" role="button" tabIndex={0}>
            <rect x={CX - 130} y={CY - 8} width="34" height="18" rx="5" fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.1)" />
            <text x={CX - 113} y={CY + 4} textAnchor="middle" fill="rgba(255,255,255,0.5)" fontSize="7">USB</text>
          </g>
          <g onClick={() => setZone("reset")} className="cursor-pointer" role="button" tabIndex={0}>
            <rect x={CX + 96} y={CY - 8} width="34" height="18" rx="5" fill="rgba(251,191,36,0.06)" stroke="rgba(251,191,36,0.25)" />
            <text x={CX + 113} y={CY + 4} textAnchor="middle" fill="rgba(251,191,36,0.75)" fontSize="7">RST</text>
          </g>

          {/* 4 nós externos nos cantos */}
          {nodes.map((n) => (
            <NodeButton key={n.id} {...n} />
          ))}
        </svg>

        <div className="relative mt-3 flex flex-wrap justify-center gap-2">
          {[
            { label: "WAN", ok: internetOk, val: hw?.internet?.ipv4 ?? "—" },
            { label: "Wi-Fi", ok: wifiActive, val: `${hw?.wifi_clients_count ?? 0} cliente(s)` },
            { label: "Redirec.", ok: (hw?.port_forwards?.length ?? 0) > 0, val: `${hw?.port_forwards?.length ?? 0} regra(s)` },
            ...((hw?.wifi ?? []).map((w) => ({
              label: w.band,
              ok: true,
              val: `${w.ssid} · ${w.security_label ?? (w.open ? "Aberta" : "WPA")}`,
            }))),
          ].map((s) => (
            <span
              key={`${s.label}-${s.val}`}
              className={cn(
                "rounded-full border px-3 py-1 text-[10px] font-medium",
                s.ok ? "border-emerald-500/25 bg-emerald-500/8 text-emerald-200" : "border-white/10 bg-white/5 text-muted-foreground",
              )}
            >
              {s.label}: {s.val}
            </span>
          ))}
        </div>
      </div>

      <div className="stitch-card flex min-h-[480px] flex-col p-5">
        {!online && (
          <p className="mb-3 rounded-xl border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
            ONT offline — comandos ficam na fila do GenieACS e aplicam no próximo Inform (~30s).
          </p>
        )}

        {status && (
          <div className={cn(
            "mb-4 flex items-start gap-2 rounded-xl border px-3 py-2.5 text-xs",
            status.type === "ok" && "border-emerald-500/30 bg-emerald-500/10 text-emerald-200",
            status.type === "err" && "border-rose-500/30 bg-rose-500/10 text-rose-200",
            status.type === "wait" && "border-cyan-500/30 bg-cyan-500/10 text-cyan-200",
          )}>
            {status.type === "err" ? <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /> : status.type === "ok" ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" /> : <Loader2 className="mt-0.5 h-4 w-4 shrink-0 animate-spin" />}
            <span>{status.text}</span>
          </div>
        )}

        <h3 className="mb-4 text-sm font-semibold">{ZONE_LABELS[zone]}</h3>

        {zone === "internet" && (
          <dl className="space-y-2 text-sm">
            {([
              ["PPPoE", hw?.internet?.pppoe_status ?? "—", internetOk],
              ["IP público", hw?.internet?.ipv4 ?? "—", true],
              ["VLAN WAN", String(hw?.internet?.vlan ?? 10), true],
              ["RX óptico", `${hw?.internet?.optical_rx_dbm ?? "—"} dBm`, true],
            ] as [string, string, boolean][]).map(([k, v, ok]) => (
              <div key={k} className="flex justify-between rounded-xl border border-white/[0.06] bg-white/[0.02] px-3 py-2.5">
                <dt className="text-muted-foreground">{k}</dt>
                <dd className={cn("font-mono text-xs", ok && k === "PPPoE" ? "text-emerald-400" : "")}>{v}</dd>
              </div>
            ))}
          </dl>
        )}

        {zone === "wifi" && (
          <div className="space-y-3">
            <div className="flex gap-2">
              {([1, 5] as const).map((idx) => {
                const net = hw?.wifi.find((w) => w.index === idx);
                return (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setWifiForm((f) => ({
                      ...f,
                      wlan_index: idx,
                      ssid: net?.ssid ?? "",
                      password: "",
                      open: net?.open ?? false,
                    }))}
                    className={cn(
                      "flex-1 rounded-xl border px-3 py-2.5 text-left text-xs transition-all",
                      wifiForm.wlan_index === idx
                        ? "border-cyan-500/40 bg-cyan-500/15 text-cyan-100"
                        : "border-white/10 bg-white/[0.02] text-muted-foreground hover:border-white/20",
                    )}
                  >
                    <span className="flex items-center gap-1.5 font-semibold">
                      {idx === 1 ? "2.4 GHz" : "5 GHz"}
                      {net?.open ? <LockOpen className="h-3 w-3 text-emerald-400" /> : <Lock className="h-3 w-3 text-amber-400" />}
                    </span>
                    <span className="mt-1 block font-mono text-[10px] opacity-80">{net?.ssid ?? "—"}</span>
                    <span className="mt-0.5 block text-[9px] opacity-60">{net?.security_label ?? "—"} · Beacon: {net?.beacon_type ?? "—"}</span>
                  </button>
                );
              })}
            </div>

            {activeWifi && (
              <div className={cn(
                "rounded-xl border px-3 py-2 text-[10px]",
                activeWifi.open ? "border-emerald-500/30 bg-emerald-500/8 text-emerald-200" : "border-amber-500/25 bg-amber-500/8 text-amber-100",
              )}>
                Estado atual: <strong>{activeWifi.security_label}</strong>
                {activeWifi.beacon_type && <> · BeaconType <code className="font-mono">{activeWifi.beacon_type}</code></>}
              </div>
            )}

            <input
              className="stitch-input text-sm"
              placeholder="Nome da rede (SSID)"
              value={wifiForm.ssid}
              onChange={(e) => setWifiForm((f) => ({ ...f, ssid: e.target.value }))}
            />
            {!wifiForm.open && (
              <input
                className="stitch-input text-sm"
                type="password"
                placeholder="Senha (mín. 8 caracteres)"
                value={wifiForm.password}
                onChange={(e) => setWifiForm((f) => ({ ...f, password: e.target.value }))}
              />
            )}
            <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-white/10 bg-white/[0.02] px-3 py-2.5 text-xs">
              <input
                type="checkbox"
                checked={wifiForm.open}
                onChange={(e) => setWifiForm((f) => ({
                  ...f,
                  open: e.target.checked,
                  password: e.target.checked ? "" : f.password,
                }))}
              />
              <span>
                <strong>Rede aberta</strong> — sem senha (BeaconType Basic)
              </span>
            </label>
            <button type="button" className="stitch-btn w-full" disabled={saving} onClick={applyWifi}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wifi className="h-4 w-4" />}
              Aplicar na ONT
            </button>
          </div>
        )}

        {(zone === "lan1" || zone === "lan2" || zone === "lan3" || zone === "lan4") && (() => {
          const idx = Number(zone.replace("lan", ""));
          const port = lanPorts.find((p) => p.index === idx);
          return (
            <div className="space-y-3">
              <div className={cn(
                "rounded-xl border p-4 text-center",
                port?.connected ? "border-emerald-500/30 bg-emerald-500/10" : "border-white/10 bg-white/[0.02]",
              )}>
                <p className="text-xs text-muted-foreground">Status físico</p>
                <p className={cn("mt-1 text-xl font-semibold", port?.connected ? "text-emerald-400" : "text-muted-foreground")}>
                  {port?.status ?? "—"}
                </p>
              </div>
              <button type="button" className="stitch-btn-ghost w-full" onClick={() => setZone("forward")}>
                <Plus className="h-4 w-4" /> Configurar redirecionamento
              </button>
            </div>
          );
        })()}

        {zone === "forward" && (
          <div className="space-y-3">
            {hw?.port_forwards?.map((r) => (
              <div key={r.index} className="flex items-center justify-between rounded-xl border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-xs">
                <div>
                  <p className="font-mono text-sm">{r.external_port} → {r.internal_client}:{r.internal_port}</p>
                  <p className="text-muted-foreground">{r.protocol}</p>
                </div>
                <button
                  type="button"
                  disabled={saving}
                  onClick={() => toggleForward(r.index, !r.enabled)}
                  className={cn("rounded-lg px-2.5 py-1 font-medium", r.enabled ? "bg-emerald-500/20 text-emerald-300" : "bg-white/5")}
                >
                  {r.enabled ? "Ativo" : "Off"}
                </button>
              </div>
            ))}
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Nova regra</p>
            <div className="grid grid-cols-2 gap-2">
              <input className="stitch-input text-xs" placeholder="Porta externa" value={pfForm.external_port} onChange={(e) => setPfForm((f) => ({ ...f, external_port: e.target.value }))} />
              <input className="stitch-input text-xs" placeholder="Porta interna" value={pfForm.internal_port} onChange={(e) => setPfForm((f) => ({ ...f, internal_port: e.target.value }))} />
            </div>
            <input className="stitch-input text-xs" placeholder="IP interno" value={pfForm.internal_client} onChange={(e) => setPfForm((f) => ({ ...f, internal_client: e.target.value }))} />
            <button type="button" className="stitch-btn w-full" disabled={saving} onClick={applyPortForward}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              Criar redirecionamento
            </button>
          </div>
        )}

        {zone === "clients" && (
          <div className="max-h-72 space-y-2 overflow-y-auto">
            {(hw?.wifi_clients?.length ?? 0) > 0 ? hw?.wifi_clients.map((c) => (
              <div key={c.mac} className="flex items-center gap-3 rounded-xl border border-white/[0.06] bg-white/[0.02] px-3 py-2.5">
                <Smartphone className="h-4 w-4 text-violet-300" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{c.name || c.mac}</p>
                  <p className="text-[10px] text-muted-foreground">{c.ssid}{c.ip ? ` · ${c.ip}` : ""}</p>
                </div>
                {c.rssi != null && <span className="font-mono text-xs text-emerald-300">{c.rssi} dBm</span>}
              </div>
            )) : <p className="text-sm text-muted-foreground">Nenhum cliente Wi-Fi conectado</p>}
          </div>
        )}

        {zone === "usb" && (
          <p className="text-sm text-muted-foreground">Porta USB para armazenamento ou impressora — configuração avançada na interface local.</p>
        )}

        {zone === "reset" && (
          <div className="rounded-xl border border-rose-500/25 bg-rose-500/10 p-4 text-sm text-rose-100">
            <RotateCcw className="mb-2 h-5 w-5" />
            Reset físico apaga TR-069. Use <strong>Restore remoto</strong> na aba Diagnósticos antes de testar reset.
          </div>
        )}
      </div>
    </div>
  );
}