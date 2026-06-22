"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Router, Stethoscope, MapPin, Clock, Radio, Settings, Activity,
  Upload, LogOut,
} from "lucide-react";
import { clearAuth, getUser } from "@/lib/auth";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/devices", label: "Equipamentos", icon: Router },
  { href: "/diagnoses", label: "Diagnósticos", icon: Stethoscope },
  { href: "/impact", label: "Impacto", icon: MapPin },
  { href: "/timeline", label: "Timeline", icon: Clock },
  { href: "/acs", label: "ACS", icon: Radio },
  { href: "/import", label: "Importar", icon: Upload },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const user = getUser();

  function logout() {
    clearAuth();
    router.push("/login");
  }

  return (
    <aside className="fixed inset-y-0 left-0 z-[100] flex h-dvh w-[72px] flex-col items-center border-r border-white/[0.06] bg-sidebar py-4 shadow-[4px_0_24px_rgba(0,0,0,0.35)] backdrop-blur-md">
      <Link href="/" className="mb-6 flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-fuchsia-600" title="Inspear ACS">
        <Activity className="h-5 w-5 text-white" />
      </Link>

      <nav className="flex flex-1 flex-col items-center gap-1">
        {nav.map((item) => {
          const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              title={item.label}
              className={cn(
                "flex h-10 w-10 items-center justify-center rounded-xl transition-all",
                active
                  ? "bg-violet-500/20 text-violet-300 ring-1 ring-violet-500/30"
                  : "text-muted-foreground hover:bg-white/[0.05] hover:text-foreground",
              )}
            >
              <item.icon className="h-[18px] w-[18px]" />
            </Link>
          );
        })}
      </nav>

      <div className="flex flex-col items-center gap-1 border-t border-white/[0.06] pt-4">
        <Link href="/settings" title="Configurações" className="flex h-10 w-10 items-center justify-center rounded-xl text-muted-foreground hover:bg-white/[0.05] hover:text-foreground">
          <Settings className="h-[18px] w-[18px]" />
        </Link>
        <button
          onClick={logout}
          title="Sair"
          className="flex h-10 w-10 items-center justify-center rounded-xl text-muted-foreground hover:bg-rose-500/10 hover:text-rose-300"
        >
          <LogOut className="h-[18px] w-[18px]" />
        </button>
        {user && (
          <div className="mt-1 flex h-8 w-8 items-center justify-center rounded-full bg-violet-500/20 text-[10px] font-bold text-violet-200" title={user.name}>
            {user.name.charAt(0).toUpperCase()}
          </div>
        )}
      </div>
    </aside>
  );
}