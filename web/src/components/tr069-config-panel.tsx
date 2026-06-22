"use client";

import { useEffect, useState } from "react";
import { Copy, Loader2, RefreshCw } from "lucide-react";
import { fetchAuthAPI } from "@/lib/auth";

interface Tr069Config {
  manufacturer: string;
  models: string[];
  menu_path: string;
  acs: { url: string; username: string; password: string };
  connection_request: { username: string; password: string };
  options: {
    enable_acs_management: boolean;
    enable_periodic_informing: boolean;
    informing_interval_seconds: number;
    informing_interval_lab_seconds: number;
  };
  ports: Record<string, number>;
  urls: Record<string, string>;
  lab_profile: {
    wan_vlan: number;
    wifi_24_ssid: string;
    wifi_5_ssid: string;
    city: string;
  };
  notes: string[];
}

function copyText(text: string) {
  void navigator.clipboard.writeText(text);
}

function ConfigRow({ label, value, mono = true }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex flex-col gap-1 border-b border-white/[0.06] py-2.5 last:border-0 sm:flex-row sm:items-center sm:justify-between">
      <span className="text-sm text-muted-foreground">{label}</span>
      <div className="flex min-w-0 items-center gap-2">
        <code className={mono ? "truncate font-mono text-xs text-foreground" : "text-sm"}>{value}</code>
        <button
          type="button"
          onClick={() => copyText(value)}
          className="shrink-0 rounded p-1 text-muted-foreground hover:bg-white/5 hover:text-foreground"
          title="Copiar"
        >
          <Copy className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

export function Tr069ConfigPanel() {
  const [cfg, setCfg] = useState<Tr069Config | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    fetchAuthAPI<Tr069Config>("/devices/tr069-config")
      .then(setCfg)
      .catch(() => setError("Não foi possível carregar a config TR-069."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  if (loading && !cfg) {
    return (
      <section className="stitch-card w-full min-w-0 p-6">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Carregando configuração TR-069…
        </div>
      </section>
    );
  }

  if (error || !cfg) {
    return (
      <section className="stitch-card w-full min-w-0 p-6">
        <p className="text-sm text-destructive">{error ?? "Config indisponível"}</p>
        <button type="button" onClick={load} className="mt-3 text-sm text-primary hover:underline">
          Tentar novamente
        </button>
      </section>
    );
  }

  return (
    <section className="stitch-card w-full min-w-0 p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-semibold">Configuração TR-069 na ONT</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {cfg.manufacturer} — {cfg.models.join(", ")} · {cfg.menu_path}
          </p>
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className="inline-flex items-center gap-1.5 rounded-lg border border-white/[0.08] px-3 py-1.5 text-xs hover:bg-white/5"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          Atualizar
        </button>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="min-w-0 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-4">
          <h3 className="mb-2 text-sm font-medium text-emerald-400">Campos na ONT (obrigatórios)</h3>
          <ConfigRow label="ACS URL" value={cfg.acs.url} />
          <ConfigRow label="ACS User Name" value={cfg.acs.username} />
          <ConfigRow label="ACS Password" value={cfg.acs.password} />
          <ConfigRow label="Connection Request User Name" value={cfg.connection_request.username} />
          <ConfigRow label="Connection Request Password" value={cfg.connection_request.password} />
          <ConfigRow
            label="Enable ACS Management"
            value={cfg.options.enable_acs_management ? "✓ Sim" : "Não"}
            mono={false}
          />
          <ConfigRow
            label="Enable Periodic Informing"
            value={cfg.options.enable_periodic_informing ? "✓ Sim" : "Não"}
            mono={false}
          />
          <ConfigRow
            label="Informing Interval (produção)"
            value={`${cfg.options.informing_interval_seconds}s`}
          />
          <ConfigRow
            label="Informing Interval (lab)"
            value={`${cfg.options.informing_interval_lab_seconds}s`}
          />
        </div>

        <div className="space-y-4">
          <div className="rounded-lg border border-white/[0.06] p-4">
            <h3 className="mb-2 text-sm font-medium">Portas do servidor</h3>
            {Object.entries(cfg.ports).map(([k, v]) => (
              <ConfigRow key={k} label={k.replace(/_/g, " ")} value={String(v)} />
            ))}
          </div>

          <div className="rounded-lg border border-white/[0.06] p-4">
            <h3 className="mb-2 text-sm font-medium">Perfil lab — {cfg.lab_profile.city}</h3>
            <ConfigRow label="WAN VLAN" value={String(cfg.lab_profile.wan_vlan)} />
            <ConfigRow label="Wi-Fi 2.4G" value={cfg.lab_profile.wifi_24_ssid} />
            <ConfigRow label="Wi-Fi 5G" value={cfg.lab_profile.wifi_5_ssid} />
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-lg border border-white/[0.06] p-4">
        <h3 className="mb-2 text-sm font-medium">URLs do sistema</h3>
        {Object.entries(cfg.urls).map(([k, v]) => (
          <ConfigRow key={k} label={k.replace(/_/g, " ")} value={v} />
        ))}
      </div>

      <ul className="mt-4 space-y-1.5 text-xs text-muted-foreground">
        {cfg.notes.map((n) => (
          <li key={n}>• {n}</li>
        ))}
      </ul>

      <p className="mt-4 text-xs text-muted-foreground">
        Documentação no repositório: <code className="font-mono">docs/tr069-config.md</code>
        {" · "}
        API: <code className="font-mono">GET /api/v1/devices/tr069-config</code>
      </p>
    </section>
  );
}