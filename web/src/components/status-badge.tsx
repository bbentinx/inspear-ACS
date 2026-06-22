import { CheckCircle2, AlertTriangle, XCircle, HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";

const config = {
  ok: { label: "OK", icon: CheckCircle2, class: "bg-emerald-500/15 text-emerald-300 border-emerald-500/25" },
  healthy: { label: "Saudável", icon: CheckCircle2, class: "bg-emerald-500/15 text-emerald-300 border-emerald-500/25" },
  connected: { label: "Conectada", icon: CheckCircle2, class: "bg-emerald-500/15 text-emerald-300 border-emerald-500/25" },
  online: { label: "Online", icon: CheckCircle2, class: "bg-emerald-500/15 text-emerald-300 border-emerald-500/25" },
  offline: { label: "Offline", icon: XCircle, class: "bg-rose-500/15 text-rose-300 border-rose-500/25" },
  warn: { label: "Atenção", icon: AlertTriangle, class: "bg-amber-500/15 text-amber-300 border-amber-500/25" },
  attention: { label: "Atenção", icon: AlertTriangle, class: "bg-amber-500/15 text-amber-300 border-amber-500/25" },
  degraded: { label: "Degradado", icon: AlertTriangle, class: "bg-amber-500/15 text-amber-300 border-amber-500/25" },
  crit: { label: "Crítico", icon: XCircle, class: "bg-rose-500/15 text-rose-300 border-rose-500/25" },
  critical: { label: "Crítico", icon: XCircle, class: "bg-rose-500/15 text-rose-300 border-rose-500/25" },
  pending: { label: "Aguardando", icon: HelpCircle, class: "bg-white/5 text-muted-foreground border-white/10" },
  info: { label: "Executado", icon: CheckCircle2, class: "bg-cyan-500/15 text-cyan-300 border-cyan-500/25" },
};

export function StatusBadge({ status, className }: { status: string; className?: string }) {
  const c = config[status as keyof typeof config] || config.pending;
  const Icon = c.icon;
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold backdrop-blur-sm", c.class, className)}>
      <Icon className="h-3.5 w-3.5" />
      {c.label}
    </span>
  );
}

export function HealthScoreRing({ score }: { score: number }) {
  const color = score >= 90 ? "#34d399" : score >= 70 ? "#fbbf24" : score >= 40 ? "#f97316" : "#f87171";
  const pct = score / 100;
  const r = 28;
  const circ = 2 * Math.PI * r;
  const dash = pct * circ;

  return (
    <div className="relative flex h-[72px] w-[72px] items-center justify-center">
      <svg className="absolute inset-0 -rotate-90" viewBox="0 0 72 72">
        <circle cx="36" cy="36" r={r} fill="none" stroke="currentColor" strokeWidth="4" className="text-white/[0.06]" />
        <circle
          cx="36" cy="36" r={r} fill="none" stroke={color} strokeWidth="4" strokeLinecap="round"
          strokeDasharray={`${dash} ${circ}`}
          className="drop-shadow-[0_0_8px_rgba(139,92,246,0.4)]"
        />
      </svg>
      <span className="relative text-xl font-bold">{score}</span>
    </div>
  );
}