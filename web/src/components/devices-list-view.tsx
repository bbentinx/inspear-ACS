"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { StatusBadge } from "@/components/status-badge";
import { StitchTopBar } from "@/components/stitch/top-bar";
import { PageContainer } from "@/components/page-container";
import { fetchAuthAPI } from "@/lib/auth";
import type { DeviceListItem } from "@/lib/types";

export function DevicesListView() {
  const [devices, setDevices] = useState<DeviceListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAuthAPI<DeviceListItem[]>("/devices")
      .then(setDevices)
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

  return (
    <PageContainer className="space-y-5">
      <StitchTopBar
        breadcrumb={[{ label: "Início", href: "/" }, { label: "Dispositivos" }]}
        title={`Equipamentos (${devices.length})`}
      />

      {devices.length === 0 ? (
        <div className="stitch-card p-12 text-center">
          <p className="text-muted-foreground">Nenhuma ONT registrada</p>
        </div>
      ) : (
        <div className="stitch-card w-full min-w-0 overflow-hidden">
          <div className="w-full overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead>
              <tr className="border-b border-white/[0.06] text-xs text-muted-foreground">
                <th className="px-4 py-3 text-left font-medium">Serial</th>
                <th className="px-4 py-3 text-left font-medium">Modelo</th>
                <th className="px-4 py-3 text-left font-medium">Cliente</th>
                <th className="px-4 py-3 text-left font-medium">Online</th>
                <th className="px-4 py-3 text-left font-medium">Health</th>
                <th className="px-4 py-3 text-left font-medium">Status</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {devices.map((d) => (
                <tr key={d.id} className="border-b border-white/[0.04] hover:bg-white/[0.03] transition-colors">
                  <td className="px-4 py-3 font-mono text-xs">{d.serial_number}</td>
                  <td className="px-4 py-3">{d.manufacturer} {d.model}</td>
                  <td className="px-4 py-3 text-muted-foreground">{d.customer_name || "—"}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center gap-1.5 ${d.is_online ? "text-emerald-400" : "text-rose-400"}`}>
                      <span className={`h-1.5 w-1.5 rounded-full ${d.is_online ? "bg-emerald-400" : "bg-rose-400"}`} />
                      {d.is_online ? "Sim" : "Não"}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-bold">{d.health_score}</td>
                  <td className="px-4 py-3"><StatusBadge status={d.health_status} /></td>
                  <td className="px-4 py-3 text-right">
                    <Link href={`/devices/${d.id}`} className="text-violet-300 hover:underline text-xs">Detalhes</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </div>
      )}
    </PageContainer>
  );
}