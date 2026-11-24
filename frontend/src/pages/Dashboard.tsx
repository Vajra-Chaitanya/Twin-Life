import { motion } from "framer-motion";
import {
  AlertTriangle,
  BrainCircuit,
  CheckCircle2,
  HeartPulse,
  RefreshCw,
  ScanLine,
  ShieldCheck,
  Siren,
  Wallet,
} from "lucide-react";
import { Link } from "react-router-dom";
import { FinancePanelBody } from "../components/dashboard/FinancePanel";
import { CardioRiskPanel, DiabetesRiskPanel, RiskExplainPanel } from "../components/dashboard/HealthRiskPanels";
import { InsurancePanelBody } from "../components/dashboard/InsurancePanel";
import { Panel } from "../components/dashboard/Panel";
import { ScoreRing } from "../components/ui/ScoreRing";
import { formatRelative } from "../lib/format";
import { type Tone } from "../lib/formulas";
import { deriveSignals } from "../lib/insights";
import { useLatestSnapshot, useReassess } from "../lib/queries";
import type { Snapshot } from "../lib/types";
import { useCurrentUser } from "../lib/user";

const TONE_TEXT: Record<Tone, string> = { good: "text-good", warn: "text-warn", risk: "text-risk" };
const TONE_BORDER: Record<Tone, string> = { good: "border-good/30", warn: "border-warn/30", risk: "border-risk/40" };
const DOMAIN_ICON = { health: HeartPulse, finance: Wallet, insurance: ShieldCheck };

const grid = { hidden: {}, show: { transition: { staggerChildren: 0.08 } } };

function EmptyState() {
  return (
    <div className="glass relative mx-auto mt-10 max-w-xl overflow-hidden p-10 text-center">
      <div className="gold-grid absolute inset-0 -z-10" />
      <ScanLine className="mx-auto h-12 w-12 text-gold" />
      <h2 className="mt-5 font-display text-2xl font-semibold text-metal">No twin calibrated yet</h2>
      <p className="mt-2 text-taupe">Calibrate a twin to light up the dashboard.</p>
      <Link to="/onboard" className="btn-gold mt-8">
        Calibrate twin
      </Link>
    </div>
  );
}

function Skeleton() {
  return (
    <div className="grid gap-5 lg:grid-cols-3" aria-busy>
      {[...Array(6)].map((_, i) => (
        <div
          key={i}
          className={`glass h-64 animate-pulse ${i === 0 ? "lg:col-span-3 h-48" : ""}`}
          style={{ animationDelay: `${i * 0.1}s` }}
        />
      ))}
    </div>
  );
}

function DashboardContent({ snapshot, onReassess, reassessing }: { snapshot: Snapshot; onReassess: () => void; reassessing: boolean }) {
  const { health: h, finance: f, insurance: i } = snapshot;
  const signals = deriveSignals(snapshot);

  return (
    <motion.div variants={grid} initial="hidden" animate="show" className="grid gap-5 lg:grid-cols-3">
      <Panel
        title="Twin vitals"
        icon={BrainCircuit}
        className="lg:col-span-3"
        subtitle={
          <>
            Twin <span className="font-mono text-champagne">{snapshot.user_id}</span> · snapshot #{snapshot.snapshot_id} ·{" "}
            {formatRelative(snapshot.created_at)}
          </>
        }
        action={
          <button type="button" onClick={onReassess} disabled={reassessing} className="btn-ghost shrink-0 px-3 py-1.5 text-xs whitespace-nowrap disabled:opacity-60">
            <RefreshCw className={`h-3.5 w-3.5 ${reassessing ? "animate-spin" : ""}`} />
            {reassessing ? "Re-assessing…" : "Re-assess"}
          </button>
        }
      >
        <div className="flex flex-wrap items-center justify-around gap-8">
          <ScoreRing value={h.overall_health_score} label="Health" color="#E0A899" />
          <ScoreRing value={f.financial_stability_score} label="Financial stability" color="#D4AF37" delay={0.15} />
          <ScoreRing value={i.insurance_adequacy_score} label="Insurance adequacy" color="#C9CED6" delay={0.3} />
        </div>
      </Panel>

      <CardioRiskPanel h={h} />
      <DiabetesRiskPanel h={h} />
      <RiskExplainPanel h={h} />

      <Panel title="Financial twin" icon={Wallet} accent="text-finance" className="lg:col-span-2">
        <FinancePanelBody finance={f} />
      </Panel>

      <Panel title="Key signals" icon={Siren} subtitle="Rule-based highlights from this snapshot">
        <ul className="flex flex-col gap-2.5">
          {signals.map((s, idx) => {
            const Icon = s.tone === "good" ? CheckCircle2 : s.tone === "risk" ? AlertTriangle : DOMAIN_ICON[s.domain];
            return (
              <motion.li
                key={s.text}
                initial={{ opacity: 0, x: 12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.4 + idx * 0.07 }}
                className={`flex gap-2.5 rounded-xl border bg-ink/40 p-3 text-sm ${TONE_BORDER[s.tone]}`}
              >
                <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${TONE_TEXT[s.tone]}`} />
                <span className="text-ivory/90">{s.text}</span>
              </motion.li>
            );
          })}
        </ul>
      </Panel>

      <Panel title="Insurance twin" icon={ShieldCheck} accent="text-insurance" className="lg:col-span-3">
        <InsurancePanelBody insurance={i} />
        <p className="mt-6 text-[11px] text-taupe/70">{i.disclaimer}</p>
      </Panel>
    </motion.div>
  );
}

export function Dashboard() {
  const userId = useCurrentUser();
  const latest = useLatestSnapshot(userId);
  const reassess = useReassess(userId);

  if (!userId) return <EmptyState />;
  if (latest.isPending) return <Skeleton />;
  if (latest.isError) {
    return (
      <div className="glass mx-auto mt-10 max-w-lg p-8 text-center">
        <AlertTriangle className="mx-auto h-10 w-10 text-risk" />
        <p className="mt-4 text-taupe">Could not load the twin. Is the backend running on port 8000?</p>
        <button type="button" onClick={() => void latest.refetch()} className="btn-gold mt-6">
          Retry
        </button>
      </div>
    );
  }
  if (!latest.data) return <EmptyState />;

  return (
    <>
      {reassess.isError && (
        <p className="mb-4 rounded-xl border border-risk/40 bg-risk/10 px-4 py-2 text-sm text-risk">
          Re-assessment failed: {reassess.error.message}
        </p>
      )}
      <DashboardContent snapshot={latest.data} onReassess={() => reassess.mutate()} reassessing={reassess.isPending} />
    </>
  );
}
