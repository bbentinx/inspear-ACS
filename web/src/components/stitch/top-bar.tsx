"use client";

import { Sparkles } from "lucide-react";
import Link from "next/link";

interface Props {
  breadcrumb?: { label: string; href?: string }[];
  title?: string;
}

export function StitchTopBar({ breadcrumb, title }: Props) {
  return (
    <header className="mb-6 flex w-full min-w-0 flex-wrap items-center justify-between gap-4">
      <div>
        {breadcrumb && breadcrumb.length > 0 && (
          <nav className="mb-1 flex items-center gap-1.5 text-xs text-muted-foreground">
            {breadcrumb.map((b, i) => (
              <span key={i} className="flex items-center gap-1.5">
                {i > 0 && <span className="opacity-40">›</span>}
                {b.href ? (
                  <Link href={b.href} className="hover:text-foreground transition-colors">{b.label}</Link>
                ) : (
                  <span className="text-foreground/80">{b.label}</span>
                )}
              </span>
            ))}
          </nav>
        )}
        {title && <h1 className="text-xl font-semibold tracking-tight">{title}</h1>}
      </div>
      <button type="button" className="stitch-btn-ghost text-fuchsia-200">
        <Sparkles className="h-4 w-4 text-fuchsia-400" />
        Assistente
      </button>
    </header>
  );
}