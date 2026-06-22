"use client";

import { useState } from "react";
import { RefreshCw, RotateCcw, Radio, Download, Loader2 } from "lucide-react";
import { fetchAuthAPI } from "@/lib/auth";

interface Props {
  deviceId: string;
  serial: string;
}

export function DeviceRemoteActions({ deviceId, serial }: Props) {
  const [loading, setLoading] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<string | null>(null);
  const [firmwareUrl, setFirmwareUrl] = useState("http://localhost:8000/examples/firmware/sample_firmware.bin");

  async function runAction(action: string, path: string, body?: object) {
    setLoading(action);
    setLastResult(null);
    try {
      const r = await fetchAuthAPI<{ ok: boolean; message: string; simulated?: boolean }>(
        path,
        { method: "POST", headers: body ? { "Content-Type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined }
      );
      setLastResult(`${r.message}${r.simulated ? " (simulado)" : ""}`);
    } catch (e) {
      setLastResult(`Erro: ${e instanceof Error ? e.message : "falha"}`);
    } finally {
      setLoading(null);
    }
  }

  return (
    <section className="stitch-card w-full min-w-0 p-4">
      <h2 className="text-sm font-semibold mb-1">Ações remotas ACS</h2>
      <p className="text-xs text-muted-foreground mb-3 font-mono">{serial}</p>
      <div className="flex flex-wrap gap-2">
        <button className="stitch-btn-ghost" disabled={!!loading} onClick={() => runAction("sync", `/devices/${deviceId}/actions/sync`)}>
          {loading === "sync" ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          Sincronizar
        </button>
        <button className="stitch-btn-ghost" disabled={!!loading} onClick={() => runAction("cr", `/devices/${deviceId}/actions/connection-request`)}>
          {loading === "cr" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Radio className="h-4 w-4" />}
          Connection Request
        </button>
        <button className="stitch-btn-ghost" disabled={!!loading} onClick={() => runAction("reboot", `/devices/${deviceId}/actions/reboot`)}>
          {loading === "reboot" ? <Loader2 className="h-4 w-4 animate-spin" /> : <RotateCcw className="h-4 w-4" />}
          Reboot
        </button>
      </div>
      <div className="mt-3 flex flex-col gap-2 sm:flex-row">
        <input value={firmwareUrl} onChange={(e) => setFirmwareUrl(e.target.value)} className="stitch-input min-w-0 flex-1 font-mono text-xs" />
        <button className="stitch-btn-ghost shrink-0 self-start sm:self-auto" disabled={!!loading} onClick={() => runAction("fw", `/devices/${deviceId}/actions/firmware-upgrade`, { firmware_url: firmwareUrl })}>
          {loading === "fw" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
          Firmware
        </button>
      </div>
      {lastResult && <p className="mt-2 text-xs rounded-lg bg-white/[0.03] px-3 py-2">{lastResult}</p>}
    </section>
  );
}