"use client";

import { useEffect, useState } from "react";
import { StatusBadge } from "@/components/status-badge";
import { PageContainer } from "@/components/page-container";
import { StitchTopBar } from "@/components/stitch/top-bar";
import { fetchAuthAPI } from "@/lib/auth";
import type { DashboardStats, ImpactGroup } from "@/lib/types";

const typeLabels: Record<string, string> = {
  pop: "POP",
  olt: "OLT/PON",
  model: "Modelo",
  cgnat: "CGNAT",
  neighborhood: "Bairro",
};

export default function ImpactPage() {
  const [groups, setGroups] = useState<ImpactGroup[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAuthAPI<DashboardStats>("/dashboard/stats")
      .then((s) => setGroups([...s.by_pop, ...s.by_model]))
      .catch(() => setGroups([]))
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
      <StitchTopBar breadcrumb={[{ label: "Início", href: "/" }, { label: "Impacto" }]} title="Mapa de impacto" />

      {groups.length === 0 ? (
        <div className="stitch-card p-12 text-center">
          <p className="text-muted-foreground">Sem agrupamentos com problemas</p>
          <p className="mt-1 text-sm text-muted-foreground">Aparece quando ONTs degradadas/críticas forem detectadas</p>
        </div>
      ) : (
        <div className="grid w-full grid-cols-1 gap-4 md:grid-cols-2">
          {groups.map((g, i) => (
            <div key={`${g.type}-${g.name}-${i}`} className="stitch-card min-w-0 p-5">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <span className="text-xs font-medium uppercase text-muted-foreground">{typeLabels[g.type] || g.type}</span>
                  <h3 className="truncate text-lg font-semibold">{g.name}</h3>
                </div>
                <StatusBadge status={g.critical > 0 ? "crit" : "warn"} />
              </div>
              {g.diagnosis && <p className="mt-2 break-words text-sm text-muted-foreground">{g.diagnosis}</p>}
              <div className="mt-4 flex flex-wrap gap-4 text-sm">
                <div><span className="font-bold text-crit">{g.critical}</span> críticos</div>
                <div><span className="font-bold text-warn">{g.degraded}</span> degradados</div>
                <div><span className="font-bold">{g.affected}</span> total afetados</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </PageContainer>
  );
}