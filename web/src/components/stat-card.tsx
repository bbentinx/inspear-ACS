import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  variant?: "default" | "ok" | "warn" | "crit";
  progress?: number;
}

export function StatCard({ title, value, subtitle, icon: Icon, variant = "default", progress }: StatCardProps) {
  const accent = {
    default: "from-violet-600/20 to-transparent border-white/[0.06]",
    ok: "from-emerald-500/20 to-transparent border-emerald-500/20",
    warn: "from-amber-500/20 to-transparent border-amber-500/20",
    crit: "from-rose-500/20 to-transparent border-rose-500/20",
  }[variant];

  const iconColor = {
    default: "text-violet-300 bg-violet-500/15 ring-violet-400/20",
    ok: "text-emerald-300 bg-emerald-500/15 ring-emerald-400/20",
    warn: "text-amber-300 bg-amber-500/15 ring-amber-400/20",
    crit: "text-rose-300 bg-rose-500/15 ring-rose-400/20",
  }[variant];

  return (
    <div className={cn("relative overflow-hidden rounded-2xl border bg-card/60 p-5 backdrop-blur-xl bg-gradient-to-br", accent)}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-muted-foreground">{title}</p>
          <p className="mt-1 text-4xl font-bold tracking-tight">{value}</p>
          {subtitle && <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>}
        </div>
        <div className={cn("rounded-xl p-2.5 ring-1", iconColor)}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
      {progress != null && (
        <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-white/[0.06]">
          <div
            className="h-full rounded-full bg-gradient-to-r from-violet-500 to-fuchsia-500 transition-all duration-700"
            style={{ width: `${Math.min(progress, 100)}%` }}
          />
        </div>
      )}
    </div>
  );
}