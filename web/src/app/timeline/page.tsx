"use client";

import { useEffect, useState } from "react";
import { StatusBadge } from "@/components/status-badge";
import { PageContainer } from "@/components/page-container";
import { StitchTopBar } from "@/components/stitch/top-bar";
import { fetchAuthAPI } from "@/lib/auth";
import type { TimelineItem } from "@/lib/types";

function formatTime(iso: string) {
  try {
    return new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
}

export default function TimelinePage() {
  const [events, setEvents] = useState<TimelineItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAuthAPI<TimelineItem[]>("/timeline")
      .then(setEvents)
      .catch(() => setEvents([]))
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
      <StitchTopBar breadcrumb={[{ label: "Início", href: "/" }, { label: "Timeline" }]} title="Timeline de incidentes" />

      {events.length === 0 ? (
        <div className="stitch-card p-12 text-center">
          <p className="text-muted-foreground">Nenhum evento registrado</p>
          <p className="mt-1 text-sm text-muted-foreground">A timeline é preenchida por Informs e alertas do ACS</p>
        </div>
      ) : (
        <div className="w-full min-w-0 space-y-0">
          {events.map((e, i) => (
            <div key={`${e.at}-${i}`} className="flex min-w-0 gap-4 pb-8">
              <div className="flex shrink-0 flex-col items-center">
                <div className="flex h-10 w-10 items-center justify-center rounded-full border-2 border-primary bg-card text-xs font-bold">
                  {formatTime(e.at)}
                </div>
                {i < events.length - 1 && <div className="mt-2 w-0.5 flex-1 bg-border" />}
              </div>
              <div className="min-w-0 flex-1 rounded-xl border border-border bg-card p-4">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="min-w-0 font-semibold">{e.title}</h3>
                  <StatusBadge status={e.severity} />
                </div>
                {e.device_serial && (
                  <p className="mt-1 truncate font-mono text-sm text-muted-foreground">{e.device_serial}</p>
                )}
                {e.description && (
                  <p className="mt-1 break-words text-sm text-muted-foreground">{e.description}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </PageContainer>
  );
}