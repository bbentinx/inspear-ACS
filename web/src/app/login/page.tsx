"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Activity, LogIn } from "lucide-react";
import { login } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("admin@inspear.local");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro no login");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center p-4">
      <div className="stitch-bg" aria-hidden />
      <div className="relative z-10 w-full max-w-md stitch-card p-8">
        <div className="mb-8 flex flex-col items-center gap-3">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-600 to-fuchsia-600">
            <Activity className="h-7 w-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold">Inspear ACS</h1>
          <p className="text-sm text-muted-foreground">Painel NOC — diagnóstico inteligente</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1.5 block text-sm font-medium">Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="stitch-input" required />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium">Senha</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="stitch-input" required />
          </div>
          {error && <p className="text-sm text-crit">{error}</p>}
          <button type="submit" disabled={loading} className="stitch-btn w-full justify-center">
            <LogIn className="h-4 w-4" />
            {loading ? "Entrando..." : "Entrar"}
          </button>
        </form>
      </div>
    </div>
  );
}