import { PageContainer } from "@/components/page-container";
import { StitchTopBar } from "@/components/stitch/top-bar";

export default function ACSPage() {
  return (
    <PageContainer className="space-y-5">
      <StitchTopBar breadcrumb={[{ label: "Início", href: "/" }, { label: "ACS" }]} title="ACS / TR-069 — GenieACS" />

      <div className="grid w-full grid-cols-1 gap-4 lg:grid-cols-2">
        <section className="stitch-card min-w-0 border-emerald-500/20 p-6">
          <h2 className="mb-3 font-semibold text-emerald-400">Fase 2 — Ativo</h2>
          <ul className="space-y-2 text-sm">
            <li>✓ Ingestão API + webhook GenieACS</li>
            <li>✓ Adapters Huawei X610</li>
            <li>✓ JWT no painel + API Key na ingestão</li>
            <li>✓ Importação CSV clientes/equipamentos</li>
          </ul>
        </section>

        <section className="stitch-card min-w-0 p-6">
          <h2 className="mb-3 font-semibold">Subir GenieACS</h2>
          <pre className="overflow-x-auto rounded-lg bg-muted p-4 text-xs font-mono">
{`docker compose \\
  -f docker-compose.yml \\
  -f genieacs/docker-compose.genieacs.yml up -d

# UI GenieACS: http://localhost:3001
# CWMP ONTs: http://SEU_IP:7547`}
          </pre>
        </section>
      </div>

      <section className="stitch-card w-full min-w-0 p-6">
        <h2 className="mb-3 font-semibold">Fluxo GenieACS → Inspear</h2>
        <div className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["1. ONT Inform", "Huawei X610 envia CWMP para :7547"],
            ["2. GenieACS", "Coleta parâmetros TR-069"],
            ["3. Provision", "Script POST webhook Inspear"],
            ["4. Diagnóstico", "Adapter → regras → Telegram"],
          ].map(([t, d]) => (
            <div key={t} className="min-w-0 rounded-lg border border-white/[0.06] p-4">
              <p className="font-medium text-primary">{t}</p>
              <p className="mt-1 text-muted-foreground">{d}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="stitch-card w-full min-w-0 p-6">
        <h2 className="mb-3 font-semibold">Endpoints</h2>
        <div className="space-y-3 font-mono text-xs">
          {[
            ["POST", "/api/v1/acs/inform", "— X-API-Key"],
            ["POST", "/api/v1/acs/genieacs/webhook", "— GenieACS provision"],
            ["POST", "/api/v1/acs/genieacs/sync/{serial}", "— pull NBI"],
            ["POST", "/api/v1/import/customers", "— JWT + CSV"],
          ].map(([method, path, note]) => (
            <div key={path} className="overflow-x-auto rounded-lg bg-muted p-3">
              <span className="text-ok">{method}</span> {path} <span className="text-muted-foreground">{note}</span>
            </div>
          ))}
        </div>
      </section>
    </PageContainer>
  );
}