"use client";

import { useCallback, useEffect, useState } from "react";
import { Activity, MapPin, Wifi, Loader2, RefreshCw, Sparkles } from "lucide-react";
import { fetchAuthAPI } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { CircularGauge } from "@/components/ui/circular-gauge";
import { SocialIcon } from "@/components/ui/social-icon";
import type { DeviceSnapshot } from "@/lib/types";

const PING_PRESETS = [
  { id: "instagram", label: "Instagram" },
  { id: "tiktok", label: "TikTok" },
  { id: "youtube", label: "YouTube" },
  { id: "facebook", label: "Facebook" },
  { id: "whatsapp", label: "WhatsApp" },
] as const;

interface PingRow {
  preset: string;
  label: string;
  avgMs?: number;
  minMs?: number;
  maxMs?: number;
  successCount?: number;
  failureCount?: number;
  okWithoutLatency?: boolean;
}

interface SpeedTestConfig {
  server_name: string;
  server_city: string;
  download_url: string;
  upload_url: string;
}

interface Props {
  deviceId: string;
  snapshot: DeviceSnapshot | null;
  isOnline?: boolean;
}

interface SpeedMetrics {
  tr069Mbps: number | null;
  wanMbps: number | null;
  tr069BytesMb?: number | null;
  wanBytesMb?: number | null;
  testedAt?: string | null;
}

interface StoredDiagnostics {
  download?: SpeedMetrics;
  upload?: SpeedMetrics;
  pings?: PingRow[];
}

function diagStorageKey(deviceId: string) {
  return `inspear:diag:${deviceId}`;
}

function loadStoredDiagnostics(deviceId: string): StoredDiagnostics {
  try {
    const raw = localStorage.getItem(diagStorageKey(deviceId));
    return raw ? (JSON.parse(raw) as StoredDiagnostics) : {};
  } catch {
    return {};
  }
}

function saveStoredDiagnostics(deviceId: string, data: StoredDiagnostics) {
  try {
    const prev = loadStoredDiagnostics(deviceId);
    localStorage.setItem(diagStorageKey(deviceId), JSON.stringify({ ...prev, ...data }));
  } catch { /* quota / private mode */ }
}

function hostToPreset(host: string): (typeof PING_PRESETS)[number] | undefined {
  const h = host.toLowerCase();
  return PING_PRESETS.find((p) => h.includes(p.id));
}

function formatTestedAt(iso?: string | null) {
  if (!iso) return null;
  try {
    return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
  } catch {
    return null;
  }
}

export function DeviceDiagnosticsDashboard({ deviceId, snapshot, isOnline = true }: Props) {
  const [band, setBand] = useState<"2.4" | "5">("2.4");
  const [loading, setLoading] = useState<string | null>(null);
  const [downloadMetrics, setDownloadMetrics] = useState<SpeedMetrics>({ tr069Mbps: null, wanMbps: null });
  const [uploadMetrics, setUploadMetrics] = useState<SpeedMetrics>({ tr069Mbps: null, wanMbps: null });
  const [pings, setPings] = useState<PingRow[]>([]);
  const [traceHost, setTraceHost] = useState("instagram");
  const [traceResult, setTraceResult] = useState<Record<string, unknown> | null>(null);
  const [traceError, setTraceError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [wlanIndex, setWlanIndex] = useState(1);
  const [ssid, setSsid] = useState("");
  const [password, setPassword] = useState("");
  const [openNetwork, setOpenNetwork] = useState(false);
  const [speedCfg, setSpeedCfg] = useState<SpeedTestConfig | null>(null);

  useEffect(() => {
    fetchAuthAPI<SpeedTestConfig>("/devices/speed-test/config").then(setSpeedCfg).catch(() => null);
  }, []);

  const applySpeedPayload = useCallback((
    payload: {
      download_mbps?: number; upload_mbps?: number; tr069_mbps?: number; bytes_mb?: number;
      wan_download_mbps?: number; wan_upload_mbps?: number; wan_bytes_mb?: number;
      state?: string;
    },
    direction: "download" | "upload",
    persist = true,
  ) => {
    const tr069 = direction === "download"
      ? (payload.tr069_mbps ?? payload.download_mbps ?? null)
      : (payload.tr069_mbps ?? payload.upload_mbps ?? null);
    const wan = (direction === "download" ? payload.wan_download_mbps : payload.wan_upload_mbps) ?? null;
    const hasValue = tr069 != null || wan != null;
    const completed = payload.state === "Completed" || payload.state === "Complete" || hasValue;
    if (!completed && tr069 == null && wan == null) return;

    const metrics: SpeedMetrics = {
      tr069Mbps: tr069 ?? null,
      wanMbps: wan,
      tr069BytesMb: payload.bytes_mb ?? null,
      wanBytesMb: payload.wan_bytes_mb ?? null,
      testedAt: new Date().toISOString(),
    };
    if (direction === "download") {
      setDownloadMetrics(metrics);
      if (persist) saveStoredDiagnostics(deviceId, { download: metrics });
    } else {
      setUploadMetrics(metrics);
      if (persist) saveStoredDiagnostics(deviceId, { upload: metrics });
    }
  }, [deviceId]);

  const upsertPingRow = useCallback((row: PingRow, persist = true) => {
    setPings((prev) => {
      const next = [...prev.filter((p) => p.preset !== row.preset), row];
      if (persist) saveStoredDiagnostics(deviceId, { pings: next });
      return next;
    });
  }, [deviceId]);

  const loadExistingResults = useCallback(async () => {
    const stored = loadStoredDiagnostics(deviceId);
    if (stored.download) setDownloadMetrics(stored.download);
    if (stored.upload) setUploadMetrics(stored.upload);
    if (stored.pings?.length) setPings(stored.pings);

    try {
      const dl = await fetchAuthAPI<{ download_mbps?: number; tr069_mbps?: number; bytes_mb?: number; wan_download_mbps?: number; wan_bytes_mb?: number; state?: string }>(`/devices/${deviceId}/diagnostics/speed`);
      const ul = await fetchAuthAPI<{ upload_mbps?: number; tr069_mbps?: number; bytes_mb?: number; wan_upload_mbps?: number; wan_bytes_mb?: number; state?: string }>(`/devices/${deviceId}/diagnostics/upload`);
      const ping = await fetchAuthAPI<{ results: Record<string, unknown> }>(`/devices/${deviceId}/diagnostics/ping`);

      const dlErr = (dl as { error?: string }).error;
      const ulErr = (ul as { error?: string }).error;
      if (dl.state === "Completed" || dl.download_mbps != null || dl.wan_download_mbps != null) {
        applySpeedPayload(dl, "download");
      } else if (dlErr) {
        setMsg(`Download: ${dlErr} — confira SPEED_TEST_DOWNLOAD_URL no .env (IP alcançável pela ONT)`);
      }
      if (ul.state === "Completed" || ul.upload_mbps != null || ul.wan_upload_mbps != null) {
        applySpeedPayload(ul, "upload");
      } else if (ulErr && !dlErr) {
        setMsg(`Upload: ${ulErr}`);
      }

      const pr = ping as { results: Record<string, unknown>; success_count?: number; ping_ok_without_latency?: boolean };
      const r = pr.results;
      if (r.Host) {
        const preset = hostToPreset(String(r.Host));
        if (preset) {
          const success = pr.success_count ?? (r.SuccessCount != null ? Number(r.SuccessCount) : undefined);
          const avg = r.AverageResponseTime != null ? Number(r.AverageResponseTime) : undefined;
          upsertPingRow({
            preset: preset.id,
            label: preset.label,
            avgMs: avg && avg > 0 ? avg : undefined,
            minMs: r.MinimumResponseTime != null ? Number(r.MinimumResponseTime) : undefined,
            maxMs: r.MaximumResponseTime != null ? Number(r.MaximumResponseTime) : undefined,
            successCount: success,
            failureCount: r.FailureCount != null ? Number(r.FailureCount) : undefined,
            okWithoutLatency: pr.ping_ok_without_latency || (success != null && success > 0 && (!avg || avg <= 0)),
          });
        }
      }
    } catch { /* mantém último salvo localmente */ }
  }, [deviceId, applySpeedPayload, upsertPingRow]);

  useEffect(() => { loadExistingResults(); }, [loadExistingResults]);

  const networks = snapshot?.wifi_networks?.filter((n) =>
    band === "2.4" ? n.band.includes("2.4") || n.index === 1 : n.band.includes("5") || n.index >= 5
  ) ?? [];

  const runPingPreset = useCallback(async (preset: string, label: string) => {
    setLoading(`ping-${preset}`);
    try {
      await fetchAuthAPI(`/devices/${deviceId}/actions/ping-test`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ preset, count: 4 }) });
      await new Promise((r) => setTimeout(r, 8000));
      const data = await fetchAuthAPI<{
        results: Record<string, unknown>;
        success_count?: number;
        ping_ok_without_latency?: boolean;
      }>(`/devices/${deviceId}/diagnostics/ping`);
      const r = data.results;
      const success = data.success_count ?? (r.SuccessCount != null ? Number(r.SuccessCount) : undefined);
      const avg = r.AverageResponseTime != null ? Number(r.AverageResponseTime) : undefined;
      upsertPingRow({
        preset, label,
        avgMs: avg && avg > 0 ? avg : undefined,
        minMs: r.MinimumResponseTime != null ? Number(r.MinimumResponseTime) : undefined,
        maxMs: r.MaximumResponseTime != null ? Number(r.MaximumResponseTime) : undefined,
        successCount: success,
        failureCount: r.FailureCount != null ? Number(r.FailureCount) : undefined,
        okWithoutLatency: data.ping_ok_without_latency || (success != null && success > 0 && (!avg || avg <= 0)),
      });
    } catch (e) {
      setMsg(`Ping ${label}: ${e instanceof Error ? e.message : "erro"}`);
    } finally { setLoading(null); }
  }, [deviceId, upsertPingRow]);

  async function runSpeedSuite() {
    setLoading("suite");
    setMsg(null);
    try {
      await Promise.all([
        fetchAuthAPI(`/devices/${deviceId}/actions/speed-test`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(speedCfg?.download_url ? { download_url: speedCfg.download_url } : {}) }),
        fetchAuthAPI(`/devices/${deviceId}/actions/upload-test`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(speedCfg?.upload_url ? { upload_url: speedCfg.upload_url } : {}) }),
        ...PING_PRESETS.slice(0, 3).map((p) => fetchAuthAPI(`/devices/${deviceId}/actions/ping-test`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ preset: p.id, count: 4 }) })),
      ]);
      let gotDl = false, gotUl = false;
      for (let i = 0; i < 6; i++) {
        await new Promise((r) => setTimeout(r, 15000));
        const dl = await fetchAuthAPI<{ download_mbps?: number; tr069_mbps?: number; bytes_mb?: number; state?: string; wan_download_mbps?: number; wan_bytes_mb?: number }>(`/devices/${deviceId}/diagnostics/speed`);
        const ul = await fetchAuthAPI<{ upload_mbps?: number; tr069_mbps?: number; bytes_mb?: number; state?: string; wan_upload_mbps?: number; wan_bytes_mb?: number }>(`/devices/${deviceId}/diagnostics/upload`);
        if (dl.download_mbps != null || dl.wan_download_mbps != null) { gotDl = dl.state === "Completed" || dl.download_mbps != null; applySpeedPayload(dl, "download"); }
        if (ul.upload_mbps != null || ul.wan_upload_mbps != null) { gotUl = ul.state === "Completed" || ul.upload_mbps != null; applySpeedPayload(ul, "upload"); }
        if (gotDl && gotUl) break;
      }
      if (!gotDl || !gotUl) await loadExistingResults();
      setMsg(gotDl && gotUl ? "Testes concluídos — último resultado salvo" : "Testes enviados — aguarde resultado (último teste permanece visível)");
    } catch (e) {
      setMsg(`Erro: ${e instanceof Error ? e.message : "falha"}`);
    } finally { setLoading(null); }
  }

  const isRunning = loading === "suite";

  return (
    <section className={cn("w-full min-w-0 max-w-full space-y-4", !isOnline && "opacity-60")}>
      {!isOnline && (
        <p className="rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-xs text-amber-200/90">
          ONT offline — testes remotos e métricas abaixo podem refletir dados antigos.
        </p>
      )}
      <div className="stitch-card w-full p-5">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <h2 className="flex items-center gap-2 text-sm font-semibold">
              <Sparkles className="h-4 w-4 shrink-0 text-fuchsia-400" />
              Teste de velocidade
            </h2>
            {speedCfg && (
              <p className="mt-1 truncate text-xs text-muted-foreground">
                Servidor: {speedCfg.server_name} · {speedCfg.server_city}
              </p>
            )}
          </div>
          <button
            onClick={runSpeedSuite}
            disabled={!!loading}
            title={!isOnline ? "ONT offline — teste entra na fila e roda no próximo Inform" : undefined}
            className="stitch-btn shrink-0"
          >
            {loading === "suite" ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            Iniciar teste
          </button>
        </div>

        {msg && <p className="mb-4 rounded-lg bg-white/[0.03] px-3 py-2 text-xs text-muted-foreground">{msg}</p>}

        {(downloadMetrics.testedAt || uploadMetrics.testedAt) && (
          <p className="mb-3 text-[10px] text-muted-foreground">
            Último teste: {formatTestedAt(downloadMetrics.testedAt ?? uploadMetrics.testedAt)}
          </p>
        )}

        <div className="grid w-full grid-cols-1 gap-4 md:grid-cols-2">
          <CircularGauge
            label="Download"
            valueMbps={downloadMetrics.tr069Mbps ?? downloadMetrics.wanMbps}
            variant="download"
            running={isRunning && downloadMetrics.tr069Mbps == null && downloadMetrics.wanMbps == null}
            secondary={[
              { label: "TR-069", value: downloadMetrics.tr069Mbps },
              { label: "WAN", value: downloadMetrics.wanMbps },
            ]}
          />
          <CircularGauge
            label="Upload"
            valueMbps={uploadMetrics.tr069Mbps ?? uploadMetrics.wanMbps}
            variant="upload"
            running={isRunning && uploadMetrics.tr069Mbps == null && uploadMetrics.wanMbps == null}
            secondary={[
              { label: "TR-069", value: uploadMetrics.tr069Mbps },
              { label: "WAN", value: uploadMetrics.wanMbps },
            ]}
          />
        </div>
      </div>

      <div className="grid w-full gap-4 lg:grid-cols-3">
        {/* Ping — coluna fixa ao rolar em telas grandes */}
        <div className="stitch-card p-5 lg:sticky lg:top-6 lg:self-start">
          <h2 className="text-sm font-semibold mb-1 flex items-center gap-2"><Activity className="h-4 w-4" /> Teste de ping</h2>
          <p className="mb-4 text-[10px] text-muted-foreground">Último resultado de cada destino permanece visível</p>
          <div className="space-y-2">
            {PING_PRESETS.map((p) => {
              const row = pings.find((x) => x.preset === p.id);
              return (
                <div key={p.id} className="flex items-center justify-between gap-2 rounded-xl border border-white/[0.06] bg-white/[0.02] px-3 py-2.5">
                  <div className="flex min-w-0 items-center gap-2.5">
                    <SocialIcon id={p.id} />
                    <span className="truncate text-sm font-medium">{p.label}</span>
                  </div>
                  <div className="flex shrink-0 items-center gap-2 text-xs font-mono">
                    {row?.minMs != null && row?.maxMs != null && (
                      <span className="hidden text-muted-foreground sm:inline">{row.minMs}–{row.maxMs}</span>
                    )}
                    <span className={cn("text-base font-bold", row?.avgMs != null || row?.okWithoutLatency ? "text-emerald-300" : "text-muted-foreground")}>
                      {row?.avgMs != null && row.avgMs > 0
                        ? <>{row.avgMs}<span className="text-[10px]">ms</span></>
                        : row?.okWithoutLatency
                          ? <span className="text-sm">{row.successCount ?? "OK"}/4 OK</span>
                          : row?.failureCount
                            ? <span className="text-sm text-rose-300">falhou</span>
                            : "—"}
                    </span>
                    <button
                      type="button"
                      disabled={!!loading}
                      onClick={() => runPingPreset(p.id, p.label)}
                      className="rounded-md px-1.5 py-0.5 text-violet-300 hover:bg-violet-500/10 disabled:opacity-40"
                      title={`Testar ${p.label}`}
                    >
                      ▶
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Traceroute + Wi-Fi */}
        <div className="stitch-card p-5 lg:col-span-2">
          <div className="grid gap-4 lg:grid-cols-2">
            <div>
              <h2 className="text-sm font-semibold mb-3 flex items-center gap-2"><MapPin className="h-4 w-4" /> Traceroute</h2>
              <select value={traceHost} onChange={(e) => setTraceHost(e.target.value)} className="stitch-input mb-2 text-xs">
                {PING_PRESETS.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
              </select>
              <button
                onClick={async () => {
                  setLoading("trace");
                  setTraceError(null);
                  try {
                    await fetchAuthAPI(`/devices/${deviceId}/actions/traceroute`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ preset: traceHost, max_hops: 8 }) });
                    await new Promise((r) => setTimeout(r, 15000));
                    const data = await fetchAuthAPI<{ results: Record<string, unknown>; supported?: boolean; error?: string }>(`/devices/${deviceId}/diagnostics/traceroute`);
                    if (data.supported === false) {
                      setTraceResult(null);
                      setTraceError(data.error ?? "Traceroute não suportado nesta ONT");
                    } else {
                      setTraceResult(data.results);
                      setTraceError(data.error ?? null);
                    }
                  } finally { setLoading(null); }
                }}
                disabled={!!loading}
                className="stitch-btn-ghost text-xs"
              >
                Executar
              </button>
              {traceError && (
                <p className="mt-2 rounded-lg border border-amber-500/25 bg-amber-500/10 px-2 py-1.5 text-[10px] text-amber-200">
                  {traceError}
                </p>
              )}
              {traceResult && !traceError && (
                <pre className="mt-2 text-[10px] font-mono bg-black/30 rounded-lg p-2 overflow-auto max-h-28 border border-white/[0.06]">
                  {JSON.stringify(traceResult, null, 2)}
                </pre>
              )}
            </div>

            <div>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold flex items-center gap-2"><Wifi className="h-4 w-4" /> Redes Wi-Fi</h2>
                <div className="flex rounded-lg border border-white/[0.08] text-[10px] overflow-hidden">
                  <button className={`px-2 py-1 ${band === "2.4" ? "bg-violet-500/20 text-violet-300" : ""}`} onClick={() => setBand("2.4")}>2.4 GHz</button>
                  <button className={`px-2 py-1 ${band === "5" ? "bg-violet-500/20 text-violet-300" : ""}`} onClick={() => setBand("5")}>5 GHz</button>
                </div>
              </div>
              {networks.map((n) => (
                <div key={n.index} className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-emerald-400" />
                    <span className="text-sm font-medium">{n.ssid}</span>
                    <span className="text-xs text-emerald-400 ml-auto">{n.clients} cliente(s)</span>
                  </div>
                  <p className="text-[10px] text-muted-foreground mt-1">Canal {n.channel ?? "—"} · {n.band}</p>
                </div>
              ))}
              <div className="mt-3 space-y-2 border-t border-white/[0.06] pt-3">
                <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Alterar rede</p>
                <select value={wlanIndex} onChange={(e) => setWlanIndex(Number(e.target.value))} className="stitch-input text-xs">
                  <option value={1}>2.4 GHz</option>
                  <option value={5}>5 GHz</option>
                </select>
                <input value={ssid} onChange={(e) => setSsid(e.target.value)} placeholder="SSID" className="stitch-input text-xs" />
                <label className="flex items-center gap-2 text-[10px] text-muted-foreground">
                  <input
                    type="checkbox"
                    checked={openNetwork}
                    onChange={(e) => {
                      setOpenNetwork(e.target.checked);
                      if (e.target.checked) setPassword("");
                    }}
                    className="rounded"
                  />
                  Rede aberta (sem senha)
                </label>
                {!openNetwork && (
                  <input
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    type="password"
                    placeholder="Senha (opcional — só altera SSID se vazio)"
                    className="stitch-input text-xs"
                  />
                )}
                <button
                  disabled={!!loading || (!ssid && !password && !openNetwork)}
                  onClick={async () => {
                    setLoading("wifi");
                    try {
                      const r = await fetchAuthAPI<{ message: string }>(`/devices/${deviceId}/actions/wifi`, {
                        method: "POST", headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                          wlan_index: wlanIndex,
                          ssid: ssid || undefined,
                          password: openNetwork ? undefined : (password || undefined),
                          open_network: openNetwork,
                        }),
                      });
                      setMsg(r.message + " — aguarde ~10s e sincronize");
                      await fetchAuthAPI(`/devices/${deviceId}/actions/sync`, { method: "POST" }).catch(() => null);
                    } catch (e) {
                      setMsg(e instanceof Error ? e.message : "Erro Wi-Fi");
                    } finally {
                      setLoading(null);
                    }
                  }}
                  className="stitch-btn-ghost w-full text-xs justify-center"
                >
                  Aplicar
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}