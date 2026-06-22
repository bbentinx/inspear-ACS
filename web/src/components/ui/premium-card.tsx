import { cn } from "@/lib/utils";

interface PremiumCardProps {
  children: React.ReactNode;
  className?: string;
  glow?: "purple" | "cyan" | "pink" | "none";
  active?: boolean;
  padding?: "sm" | "md" | "lg";
}

const glowMap = {
  purple: "shadow-[0_0_40px_-12px_rgba(139,92,246,0.45)] border-violet-500/25",
  cyan: "shadow-[0_0_40px_-12px_rgba(34,211,238,0.35)] border-cyan-500/25",
  pink: "shadow-[0_0_50px_-8px_rgba(236,72,153,0.55)] border-fuchsia-500/40",
  none: "border-white/[0.06]",
};

const padMap = { sm: "p-4", md: "p-5", lg: "p-6" };

export function PremiumCard({
  children,
  className,
  glow = "none",
  active = false,
  padding = "md",
}: PremiumCardProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-2xl border bg-card/70 backdrop-blur-xl",
        "before:pointer-events-none before:absolute before:inset-0 before:rounded-2xl",
        "before:bg-gradient-to-br before:from-white/[0.04] before:to-transparent",
        glowMap[glow],
        active && "ring-1 ring-fuchsia-400/50 animate-pulse-glow",
        padMap[padding],
        className,
      )}
    >
      {children}
    </div>
  );
}

export function PremiumSectionHeader({
  title,
  subtitle,
  action,
  icon: Icon,
}: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
  icon?: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
      <div className="flex items-start gap-3">
        {Icon && (
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/15 ring-1 ring-primary/25">
            <Icon className="h-4 w-4 text-primary" />
          </div>
        )}
        <div>
          <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
          {subtitle && <p className="mt-0.5 text-sm text-muted-foreground">{subtitle}</p>}
        </div>
      </div>
      {action}
    </div>
  );
}