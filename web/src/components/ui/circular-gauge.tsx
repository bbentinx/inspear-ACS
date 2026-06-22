"use client";

import { ArrowDown, ArrowUp } from "lucide-react";
import { cn } from "@/lib/utils";

interface CircularGaugeProps {
  label: string;
  valueMbps: number | null;
  variant: "download" | "upload";
  running?: boolean;
  secondary?: { label: string; value: number | null }[];
  className?: string;
}

const styles = {
  download: {
    ring: "stroke-violet-400/70",
    icon: "bg-violet-500/20 text-violet-300",
    accent: "text-violet-100",
  },
  upload: {
    ring: "stroke-cyan-400/70",
    icon: "bg-cyan-500/20 text-cyan-300",
    accent: "text-cyan-100",
  },
};

export function CircularGauge({
  label,
  valueMbps,
  variant,
  running = false,
  secondary = [],
  className,
}: CircularGaugeProps) {
  const s = styles[variant];
  const mbps = valueMbps != null ? valueMbps.toFixed(1) : "—";
  const mbs = valueMbps != null ? (valueMbps / 8).toFixed(1) : "—";
  const Icon = variant === "download" ? ArrowDown : ArrowUp;

  return (
    <div
      className={cn(
        "flex w-full min-w-0 flex-col items-stretch rounded-2xl border border-white/[0.06] bg-black/25 px-5 py-6 stitch-dots-bg",
        running && "stitch-running",
        className,
      )}
    >
      {/* Anel + valor central — altura fixa, sem absolute no container pai */}
      <div className="relative mx-auto flex h-[240px] w-full max-w-[280px] items-center justify-center">
        <svg
          className="pointer-events-none absolute h-[220px] w-[220px]"
          viewBox="0 0 200 200"
          aria-hidden
        >
          <circle cx="100" cy="100" r="88" fill="none" strokeWidth="2" className={s.ring} />
        </svg>

        <div className="relative z-10 flex max-w-[180px] flex-col items-center text-center">
          <div className={cn("mb-2 flex h-9 w-9 shrink-0 items-center justify-center rounded-full", s.icon)}>
            <Icon className="h-4 w-4" />
          </div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className={cn("mt-1 text-3xl font-bold leading-none tracking-tight sm:text-4xl", s.accent)}>
            {mbps}
          </p>
          <p className="mt-1 text-sm font-normal text-muted-foreground">Mbps</p>
          <p className="mt-3 text-xs text-muted-foreground">{running ? "Medindo…" : "Último teste"}</p>
          <p className="text-sm font-medium">{mbs} MB/s</p>
          {running && (
            <p className="mt-2 text-xs font-medium text-fuchsia-300">Teste em execução</p>
          )}
        </div>
      </div>

      {secondary.length > 0 && (
        <div className="mt-2 grid w-full grid-cols-2 gap-3 border-t border-white/[0.06] pt-4">
          {secondary.map((item) => (
            <div
              key={item.label}
              className="rounded-xl border border-white/[0.06] bg-white/[0.03] px-3 py-2.5 text-center"
            >
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{item.label}</p>
              <p className="mt-0.5 text-lg font-semibold leading-tight">
                {item.value != null ? item.value : "—"}
                <span className="text-[10px] font-normal text-muted-foreground"> Mbps</span>
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}