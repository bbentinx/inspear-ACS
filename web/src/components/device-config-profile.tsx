"use client";

import { useCallback, useEffect, useState } from "react";
import { Shield, Save, RotateCcw, Loader2, AlertTriangle, HardDrive } from "lucide-react";
import { fetchAuthAPI } from "@/lib/auth";

interface CityProfile {
  code: string;
  city?: string;
  wan_vlan?: number;
  description?: string;
}

interface ConfigProfile {
  acs_url?: string | null;
  wan_vlan?: number | null;
  acs_username?: string | null;
  acs_password?: string | null;
  cr_username?: string | null;
  cr_password?: string | null;
  pppoe_username?: string | null;
  pppoe_password?: string | null;
  wifi_24_ssid?: string | null;
  wifi_24_password?: string | null;
  wifi_5_ssid?: string | null;
  wifi_5_password?: string | null;
  auto_restore_enabled?: boolean;
  last_captured_at?: string | null;
  last_applied_at?: string | null;
}

interface Props {
  deviceId: string;
  serial: string;
}

export function DeviceConfigProfile({ deviceId, serial }: Props) {
  const [profile, setProfile] = useState<ConfigProfile | null>(null);
  const [cities, setCities] = useState<CityProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [form, setForm] = useState<ConfigProfile>({ auto_restore_enabled: true });

  const load = useCallback(async () => {
    try {
      const r = await fetchAuthAPI<{ ok: boolean; profile: ConfigProfile | null }>(
        `/devices/${deviceId}/config-profile`,
      );
      if (r.profile) {
        setProfile(r.profile);
        setForm(r.profile);
      }
    } catch {
      setProfile(null);
    } finally {
      setLoading(false);
    }
  }, [deviceId]);

  useEffect(() => {
    load();
    fetchAuthAPI<{ cities: CityProfile[] }>("/devices/provisioning/cities")
      .then((r) => setCities(r.cities))
      .catch(() => null);
  }, [load]);

  async function run(action: "capture" | "restore" | "save" | "city" | "isp-default") {
    setSaving(true);
    setMsg(null);
    try {
      if (action === "save") {
        const r = await fetchAuthAPI<{ ok: boolean; profile: ConfigProfile }>(
          `/devices/${deviceId}/config-profile`,
          { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(form) },
        );
        setProfile(r.profile);
        setForm(r.profile);
        setMsg("Perfil salvo");
      } else if (action === "isp-default") {
        const r = await fetchAuthAPI<{
          message: string;
          genieacs_task?: { steps?: Array<{ step?: string; verified?: boolean }> };
        }>(
          `/devices/${deviceId}/actions/save-isp-default`,
          { method: "POST" },
        );
        const verified = r.genieacs_task?.steps?.find(
          (s) => s.step === "autoBackupRestorePointVerify",
        )?.verified;
        setMsg(
          r.message +
            (verified === false
              ? " — backup na flash não confirmado; repita após ONT online"
              : verified
                ? " — backup na flash OK; pode testar reset"
                : " — confira backup na ONT antes de resetar"),
        );
        await load();
      } else if (action === "city") {
        const r = await fetchAuthAPI<{ message: string }>(
          `/devices/${deviceId}/actions/apply-city-profile?city_code=fernandopolis`,
          { method: "POST" },
        );
        setMsg(r.message);
        await load();
      } else {
        const r = await fetchAuthAPI<{ message: string }>(
          `/devices/${deviceId}/actions/${action === "capture" ? "capture-config" : "restore-config"}`,
          { method: "POST" },
        );
        setMsg(r.message);
        await load();
      }
    } catch (e) {
      setMsg(`Erro: ${e instanceof Error ? e.message : "falha"}`);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="stitch-card flex justify-center p-6">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <section className="stitch-card w-full min-w-0 p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="flex items-center gap-2 text-sm font-semibold">
            <Shield className="h-4 w-4 text-cyan-300" />
            Restore remoto pós-reset
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Salva PPPoE, Wi-Fi e ACS para reaplicar sem visita técnica · {serial}
          </p>
        </div>
        <label className="flex items-center gap-2 text-xs text-muted-foreground">
          <input
            type="checkbox"
            checked={form.auto_restore_enabled ?? true}
            onChange={(e) => setForm((f) => ({ ...f, auto_restore_enabled: e.target.checked }))}
            className="rounded"
          />
          Auto-restore no boot
        </label>
      </div>

      {cities.length > 0 && (
        <div className="mb-3 flex flex-wrap items-center gap-2">
          {cities.map((c) => (
            <span
              key={c.code}
              className="rounded-lg border border-cyan-500/25 bg-cyan-500/10 px-2.5 py-1 text-[10px] text-cyan-200"
            >
              {c.city} · VLAN {c.wan_vlan}
            </span>
          ))}
        </div>
      )}

      <div className="mb-3 space-y-2">
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-xs text-amber-200/90">
          <AlertTriangle className="mr-1 inline h-3.5 w-3.5" />
          Cadastre a <strong>senha PPPoE</strong> — a ONT não devolve essa senha via TR-069.
          Sem ela, só Wi-Fi e ACS são restaurados.
        </div>
        <div className="rounded-lg border border-rose-500/25 bg-rose-500/5 px-3 py-2 text-xs text-rose-200/90">
          <AlertTriangle className="mr-1 inline h-3.5 w-3.5" />
          <strong>Reset pelo botão físico</strong> apaga o TR-069. A ONT só volta ao ACS se o
          backup na flash estiver gravado (<em>Gravar padrão na ONT</em> com backup confirmado)
          ou se alguém configurar o ACS URL em <code className="text-[10px]">192.168.100.1</code> após o reset.
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <p className="mb-1 text-[10px] uppercase tracking-wide text-muted-foreground">
            PPPoE · VLAN WAN {form.wan_vlan ?? 10}
          </p>
          <input
            className="stitch-input mb-2 text-xs w-20 inline-block mr-2"
            type="number"
            placeholder="VLAN"
            value={form.wan_vlan ?? 10}
            onChange={(e) => setForm((f) => ({ ...f, wan_vlan: Number(e.target.value) }))}
          />
          <input
            className="stitch-input mb-2 text-xs inline-block flex-1 min-w-[140px]"
            placeholder="Usuário PPPoE"
            value={form.pppoe_username ?? ""}
            onChange={(e) => setForm((f) => ({ ...f, pppoe_username: e.target.value }))}
          />
          <input
            className="stitch-input text-xs"
            type="password"
            placeholder="Senha PPPoE"
            value={form.pppoe_password ?? ""}
            onChange={(e) => setForm((f) => ({ ...f, pppoe_password: e.target.value }))}
          />
        </div>
        <div>
          <p className="mb-1 text-[10px] uppercase tracking-wide text-muted-foreground">Wi-Fi 2.4G / 5G</p>
          <input
            className="stitch-input mb-2 text-xs"
            placeholder="SSID 2.4G"
            value={form.wifi_24_ssid ?? ""}
            onChange={(e) => setForm((f) => ({ ...f, wifi_24_ssid: e.target.value }))}
          />
          <input
            className="stitch-input mb-2 text-xs"
            type="password"
            placeholder="Senha 2.4G"
            value={form.wifi_24_password ?? ""}
            onChange={(e) => setForm((f) => ({ ...f, wifi_24_password: e.target.value }))}
          />
          <input
            className="stitch-input mb-2 text-xs"
            placeholder="SSID 5G"
            value={form.wifi_5_ssid ?? ""}
            onChange={(e) => setForm((f) => ({ ...f, wifi_5_ssid: e.target.value }))}
          />
          <input
            className="stitch-input text-xs"
            type="password"
            placeholder="Senha 5G"
            value={form.wifi_5_password ?? ""}
            onChange={(e) => setForm((f) => ({ ...f, wifi_5_password: e.target.value }))}
          />
        </div>
        <div className="sm:col-span-2">
          <p className="mb-1 text-[10px] uppercase tracking-wide text-muted-foreground">ACS (TR-069)</p>
          <input
            className="stitch-input text-xs font-mono"
            placeholder="ACS URL — ex: http://IP:7547"
            value={form.acs_url ?? ""}
            onChange={(e) => setForm((f) => ({ ...f, acs_url: e.target.value }))}
          />
        </div>
      </div>

      {(profile?.last_captured_at || profile?.last_applied_at) && (
        <p className="mt-3 text-[10px] text-muted-foreground">
          {profile.last_captured_at && <>Capturado: {new Date(profile.last_captured_at).toLocaleString("pt-BR")}</>}
          {profile.last_applied_at && <> · Aplicado: {new Date(profile.last_applied_at).toLocaleString("pt-BR")}</>}
        </p>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        <button className="stitch-btn-ghost" disabled={saving} onClick={() => run("city")} title="Padrão Fernandópolis VLAN 10">
          Padrão Fernandópolis
        </button>
        <button className="stitch-btn-ghost" disabled={saving} onClick={() => run("capture")}>
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          Capturar da ONT
        </button>
        <button className="stitch-btn-ghost" disabled={saving} onClick={() => run("save")}>
          <Save className="h-4 w-4" /> Salvar perfil
        </button>
        <button className="stitch-btn" disabled={saving} onClick={() => run("restore")}>
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <RotateCcw className="h-4 w-4" />}
          Restaurar agora
        </button>
        <button
          className="stitch-btn bg-gradient-to-r from-cyan-600 to-violet-600 hover:opacity-90"
          disabled={saving}
          onClick={() => run("isp-default")}
          title="Grava PPPoE + VLAN 10 + ACS + Wi-Fi como padrão de fábrica na ONT"
        >
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <HardDrive className="h-4 w-4" />}
          Gravar padrão na ONT
        </button>
      </div>
      {msg && <p className="mt-2 rounded-lg bg-white/[0.03] px-3 py-2 text-xs">{msg}</p>}
    </section>
  );
}