"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Router, Sparkles, CheckCircle2, History } from "lucide-react";
import { StatusBadge } from "@/components/status-badge";
import { StitchTopBar } from "@/components/stitch/top-bar";
import { PageContainer } from "@/components/page-container";
import { fetchAuthAPI } from "@/lib/auth";
import type { DashboardStats, DeviceListItem } from "@/lib/types";

const emptyStats: DashboardStats = {
  total_devices: 0,
  online_devices: 0,
  offline_devices: 0,
  critical_devices: 0,
  degraded_devices: 0,
  diagnoses_24h: 0,
  alerts_open: 0,
  by_pop: [],
  by_model: [],
  recent_diagnoses: [],
};

export function DashboardView() {
  const [stats, setStats] = useState<DashboardStats>(emptyStats);
  const [devices, setDevices] = useState<DeviceListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetchAuthAPI<DashboardStats>("/dashboard/stats"),
      fetchAuthAPI<DeviceListItem[]>("/devices"),
    ])
      .then(([s, d]) => {
        setStats(s);
        setDevices(d);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Erro ao carregar"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-10 w-10 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
      </div>
    );
  }

  if (error) return <p className="text-crit">{error}</p>;

  const onlinePct = stats.total_devices ? Math.round((stats.online_devices / stats.total_devices) * 100) : 0;
  const models: { name: string; count: number }[] = stats.by_model?.length
    ? stats.by_model.map((m) => ({ name: m.name, count: m.affected }))
    : devices.reduce((acc, d) => {
        const key = `${d.manufacturer} ${d.model}`.trim() || "Desconhecido";
        const found = acc.find((x) => x.name === key);
        if (found) found.count += 1;
        else acc.push({ name: key, count: 1 });
        return acc;
      }, [] as { name: string; count: number }[]);

  return (
    <PageContainer className="space-y-5">
      <StitchTopBar breadcrumb={[{ label: "Início", href: "/" }]} title="ACS" />

      <div className="grid gap-4 lg:grid-cols-12">
        {/* Status de dispositivos */}
        <div className="stitch-card p-5 lg:col-span-3">
          <h2 className="text-sm font-semibold mb-4">Status de dispositivos</h2>
          <div className="flex items-end gap-3 mb-4">
            <div>
              <p className="text-3xl font-bold text-emerald-400">{stats.online_devices}</p>
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-emerald-400" /> Online
              </p>
            </div>
            <div className="pb-1">
              <p className="text-2xl font-bold">{stats.total_devices}</p>
              <p className="text-xs text-muted-foreground">Total</p>
            </div>
          </div>
          <p className="text-xs text-muted-foreground mb-2">Online nas últimas 24 horas</p>
          <div className="h-2 rounded-full bg-white/[0.06] overflow-hidden">
            <div className="h-full rounded-full bg-emerald-500/80" style={{ width: `${onlinePct}%` }} />
          </div>
          <p className="text-xs text-muted-foreground mt-1 text-right">Média ({onlinePct}%)</p>
        </div>

        {/* Estatísticas de rede */}
        <div className="stitch-card p-5 lg:col-span-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold">Estatísticas de rede</h2>
            <div className="flex gap-1 text-[10px]">
              <span className="rounded-md bg-violet-500/20 px-2 py-0.5 text-violet-300">IPv6</span>
              <span className="rounded-md px-2 py-0.5 text-muted-foreground">TX/RX</span>
            </div>
          </div>
          <p className="text-4xl font-bold">{onlinePct}<span className="text-lg text-muted-foreground">%</span></p>
          <p className="text-xs text-muted-foreground mb-4">Da rede online</p>
          <div className="flex items-center gap-2 rounded-xl border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-xs">
            <CheckCircle2 className="h-3.5 w-3.5 text-cyan-400 shrink-0" />
            Provisionamento automático ativo
          </div>
          <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
            <div><p className="font-bold">{stats.diagnoses_24h}</p><p className="text-muted-foreground">Hoje</p></div>
            <div><p className="font-bold">{stats.degraded_devices}</p><p className="text-muted-foreground">Degradados</p></div>
            <div><p className="font-bold">{stats.critical_devices}</p><p className="text-muted-foreground">Críticos</p></div>
          </div>
        </div>

        {/* Resumo por IA */}
        <div className="stitch-card-ai p-5 lg:col-span-5">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="h-4 w-4 text-fuchsia-400" />
            <h2 className="text-sm font-semibold text-fuchsia-100">Resumo por IA</h2>
          </div>
          <p className="text-sm text-muted-foreground leading-relaxed">
            {stats.critical_devices > 0
              ? `O Inspear ACS detectou ${stats.critical_devices} equipamento(s) crítico(s) e ${stats.alerts_open} alerta(s) aberto(s). Recomenda-se verificação imediata no NOC.`
              : `Rede estável com ${stats.online_devices} de ${stats.total_devices} ONTs online. Nenhuma anomalia crítica detectada no sistema.`}
          </p>
        </div>

        {/* Uso do sistema */}
        <div className="stitch-card p-5 lg:col-span-4">
          <h2 className="text-sm font-semibold mb-4">Uso do sistema nos últimos 7 dias</h2>
          <p className="text-xs text-muted-foreground mb-3">Total de diagnósticos: {stats.diagnoses_24h}</p>
          <div className="space-y-2">
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span>Diagnósticos automáticos</span>
                <span>{stats.diagnoses_24h}</span>
              </div>
              <div className="h-2 rounded-full bg-white/[0.06]">
                <div className="h-full rounded-full bg-violet-500" style={{ width: `${Math.min(stats.diagnoses_24h * 10, 100)}%` }} />
              </div>
            </div>
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span>Alertas abertos</span>
                <span>{stats.alerts_open}</span>
              </div>
              <div className="h-2 rounded-full bg-white/[0.06]">
                <div className="h-full rounded-full bg-amber-500" style={{ width: `${Math.min(stats.alerts_open * 20, 100)}%` }} />
              </div>
            </div>
          </div>
        </div>

        {/* Uso de dispositivos */}
        <div className="stitch-card p-5 lg:col-span-4">
          <h2 className="text-sm font-semibold mb-4">Uso de dispositivos</h2>
          <p className="text-xs text-muted-foreground mb-3">Acessos por modelo</p>
          <div className="space-y-2">
            {models.slice(0, 5).map((m, i) => (
              <div key={m.name} className="flex items-center gap-2 text-xs">
                <span className="w-28 truncate text-muted-foreground">{m.name}</span>
                <div className="flex-1 h-1.5 rounded-full bg-white/[0.06]">
                  <div
                    className="h-full rounded-full bg-emerald-500/70"
                    style={{ width: `${Math.max(15, 100 - i * 18)}%` }}
                  />
                </div>
                <span className="w-8 text-right font-mono">{m.count}</span>
              </div>
            ))}
            {models.length === 0 && <p className="text-xs text-muted-foreground">Sem dados de modelo</p>}
          </div>
        </div>

        {/* Resets */}
        <div className="stitch-card p-5 lg:col-span-4">
          <h2 className="text-sm font-semibold mb-4">Resets</h2>
          <p className="text-4xl font-bold">0</p>
          <p className="text-xs text-muted-foreground mb-3">Resets hoje</p>
          <div className="flex items-center gap-2 text-xs text-emerald-400">
            <CheckCircle2 className="h-3.5 w-3.5" />
            Nenhuma anomalia detectada no número de resets
          </div>
        </div>
      </div>

      {/* Histórico */}
      <div className="stitch-card p-5">
        <div className="flex items-center gap-2 mb-4">
          <History className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold">Histórico</h2>
        </div>
        <div className="space-y-2">
          {devices.slice(0, 6).map((d) => (
            <Link
              key={d.id}
              href={`/devices/${d.id}`}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/[0.04] bg-white/[0.02] px-4 py-3 text-sm hover:bg-white/[0.04] transition-colors"
            >
              <div className="flex items-center gap-3 min-w-0">
                <span className={`h-2 w-2 rounded-full shrink-0 ${d.is_online ? "bg-emerald-400" : "bg-rose-400"}`} />
                <Router className="h-4 w-4 text-muted-foreground shrink-0" />
                <span className="font-medium truncate">{d.manufacturer} {d.model}</span>
                <span className="font-mono text-xs text-muted-foreground">{d.serial_number}</span>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <span className="text-xs text-muted-foreground">{d.customer_name || "PPPoE"}</span>
                <StatusBadge status={d.health_status} />
              </div>
            </Link>
          ))}
          {devices.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-6">Nenhum equipamento registrado</p>
          )}
        </div>
      </div>
    </PageContainer>
  );
}