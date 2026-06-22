"use client";

import { useEffect, useState } from "react";
import { StatusBadge } from "@/components/status-badge";
import { PageContainer } from "@/components/page-container";
import { StitchTopBar } from "@/components/stitch/top-bar";
import { fetchAuthAPI } from "@/lib/auth";
import type { RecentDiagnosis } from "@/lib/types";

const teamColors: Record<string, string> = {
  field: "bg-orange-500/15 text-orange-400",
  noc: "bg-primary/15 text-primary",
  support: "bg-blue-500/15 text-blue-400",
  upstream: "bg-purple-500/15 text-purple-400",
};

export default function DiagnosesPage() {
  const [diagnoses, setDiagnoses] = useState<RecentDiagnosis[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAuthAPI<RecentDiagnosis[]>("/diagnoses/list")
      .then(setDiagnoses)
      .catch(() => setDiagnoses([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <PageContainer className="space-y-5">
      <StitchTopBar breadcrumb={[{ label: "Início", href: "/" }, { label: "Diagnósticos" }]} title="Diagnósticos automáticos" />

      {diagnoses.length === 0 ? (
        <div className="stitch-card p-12 text-center">
          <p className="text-muted-foreground">Nenhum diagnóstico ativo</p>
          <p className="mt-1 text-sm text-muted-foreground">Os diagnósticos aparecem após Inform das ONTs</p>
        </div>
      ) : (
        <div className="grid w-full gap-4">
          {diagnoses.map((d) => (
            <div key={d.id} className="stitch-card min-w-0 p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="text-lg font-semibold">{d.problem_label}</h3>
                  <p className="truncate text-sm font-mono text-muted-foreground">
                    {d.device_serial} — {d.customer_name || "Sem cliente"}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <StatusBadge status={d.severity} />
                  {d.responsible_team && (
                    <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${teamColors[d.responsible_team] || ""}`}>
                      {d.responsible_team.toUpperCase()}
                    </span>
                  )}
                </div>
              </div>
              {d.confidence != null && (
                <div className="mt-3 flex min-w-0 items-center gap-4">
                  <div className="h-2 min-w-0 flex-1 overflow-hidden rounded-full bg-muted">
                    <div className="h-full rounded-full bg-primary" style={{ width: `${d.confidence}%` }} />
                  </div>
                  <span className="shrink-0 text-sm font-medium">{d.confidence}% confiança</span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </PageContainer>
  );
}