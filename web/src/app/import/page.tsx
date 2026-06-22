"use client";

import { useState } from "react";
import { Upload, FileSpreadsheet, CheckCircle2, AlertCircle } from "lucide-react";
import { getToken } from "@/lib/auth";
import { API_URL } from "@/lib/utils";
import { PageContainer } from "@/components/page-container";
import { StitchTopBar } from "@/components/stitch/top-bar";

interface ImportResult {
  created: number;
  updated: number;
  skipped: number;
  errors: string[];
}

export default function ImportPage() {
  const [customersResult, setCustomersResult] = useState<ImportResult | null>(null);
  const [devicesResult, setDevicesResult] = useState<ImportResult | null>(null);
  const [loading, setLoading] = useState<string | null>(null);

  async function upload(type: "customers" | "devices", file: File) {
    setLoading(type);
    const form = new FormData();
    form.append("file", file);
    const token = getToken();
    try {
      const r = await fetch(`${API_URL}/api/v1/import/${type}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || "Erro na importação");
      if (type === "customers") setCustomersResult(data);
      else setDevicesResult(data);
    } catch (e) {
      const err = { created: 0, updated: 0, skipped: 0, errors: [String(e)] };
      if (type === "customers") setCustomersResult(err);
      else setDevicesResult(err);
    } finally {
      setLoading(null);
    }
  }

  function ResultBox({ result, title }: { result: ImportResult | null; title: string }) {
    if (!result) return null;
    const ok = result.errors.length === 0;
    return (
      <div className={`mt-4 rounded-lg border p-4 ${ok ? "border-ok/30 bg-ok/5" : "border-warn/30 bg-warn/5"}`}>
        <div className="flex items-center gap-2 mb-2">
          {ok ? <CheckCircle2 className="h-4 w-4 text-ok" /> : <AlertCircle className="h-4 w-4 text-warn" />}
          <span className="font-medium">{title}</span>
        </div>
        <p className="text-sm">
          Criados: <strong>{result.created}</strong> · Atualizados: <strong>{result.updated}</strong> · Ignorados: <strong>{result.skipped}</strong>
        </p>
        {result.errors.length > 0 && (
          <ul className="mt-2 text-xs text-crit space-y-1">
            {result.errors.map((e, i) => <li key={i}>{e}</li>)}
          </ul>
        )}
      </div>
    );
  }

  return (
    <PageContainer className="space-y-5">
      <StitchTopBar breadcrumb={[{ label: "Início", href: "/" }, { label: "Importar" }]} title="Importação CSV" />

      <div className="grid w-full grid-cols-1 gap-5 lg:grid-cols-2">
        <div>
          <UploadCard
            title="Clientes"
            description="name, pppoe_login, phone, address, neighborhood, pop_id"
            templateHref="/templates/customers_import.csv"
            loading={loading === "customers"}
            onUpload={(f) => upload("customers", f)}
          />
          <ResultBox result={customersResult} title="Resultado — Clientes" />
        </div>
        <div>
          <UploadCard
            title="Equipamentos (ONTs)"
            description="serial_number, manufacturer, model, pppoe_login, pop_id, olt_id, pon_id, onu_id"
            templateHref="/templates/devices_import.csv"
            loading={loading === "devices"}
            onUpload={(f) => upload("devices", f)}
          />
          <ResultBox result={devicesResult} title="Resultado — Equipamentos" />
        </div>
      </div>

      <section className="stitch-card w-full p-6 lg:col-span-2">
        <h2 className="mb-3 font-semibold">Ordem recomendada</h2>
        <ol className="list-inside list-decimal space-y-2 text-sm text-muted-foreground">
          <li>Importe <strong className="text-foreground">clientes</strong> primeiro (vínculo por pppoe_login)</li>
          <li>Importe <strong className="text-foreground">equipamentos</strong> com serial e pppoe_login</li>
          <li>Configure GenieACS ou envie Informs via API</li>
        </ol>
      </section>
    </PageContainer>
  );
}

function UploadCard({
  title, description, templateHref, loading, onUpload,
}: {
  title: string;
  description: string;
  templateHref: string;
  loading: boolean;
  onUpload: (f: File) => void;
}) {
  return (
    <div className="stitch-card min-w-0 p-6">
      <div className="flex items-center gap-3 mb-4">
        <FileSpreadsheet className="h-8 w-8 text-primary" />
        <div>
          <h3 className="font-semibold">{title}</h3>
          <p className="text-xs text-muted-foreground">{description}</p>
        </div>
      </div>
      <label className="flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed border-border bg-muted/20 p-8 hover:bg-muted/40 transition-colors">
        <Upload className="h-8 w-8 text-muted-foreground" />
        <span className="text-sm font-medium">{loading ? "Importando..." : "Clique ou arraste o CSV"}</span>
        <input
          type="file"
          accept=".csv"
          className="hidden"
          disabled={loading}
          onChange={(e) => e.target.files?.[0] && onUpload(e.target.files[0])}
        />
      </label>
      <a href={templateHref} download className="mt-3 block text-center text-xs text-primary hover:underline">
        Baixar modelo CSV
      </a>
    </div>
  );
}