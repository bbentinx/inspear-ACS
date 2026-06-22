"use client";

import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/sidebar";
import { AuthGuard } from "@/components/auth-guard";

const SIDEBAR_W = 72;

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isLogin = pathname === "/login";

  return (
    <AuthGuard>
      <div className="stitch-bg" aria-hidden />
      {isLogin ? (
        <div className="relative z-10 min-h-screen w-full overflow-x-hidden">{children}</div>
      ) : (
        <>
          <Sidebar />
          <main
            className="relative z-10 min-h-dvh min-w-0 overflow-x-hidden px-4 py-5 sm:px-6 lg:px-8 lg:py-6"
            style={{ marginLeft: SIDEBAR_W, width: `calc(100% - ${SIDEBAR_W}px)` }}
          >
            {children}
          </main>
        </>
      )}
    </AuthGuard>
  );
}