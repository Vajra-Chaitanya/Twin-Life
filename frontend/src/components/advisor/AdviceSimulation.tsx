import { useMutation } from "@tanstack/react-query";
import { FlaskConical, RefreshCcw, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { simulate, simulateAdvice } from "../../lib/api";
import type { AdviceChange, Profiles, SimulateRequest, Twin } from "../../lib/types";

const BINARY = new Set(["smoke", "alco", "active"]);

function display(change: AdviceChange, value: AdviceChange["target"]) {
  if (Array.isArray(value)) return value.length ? value.join(", ") : "None";
  if (BINARY.has(change.field)) return value ? "Yes" : "No";
  if (change.label.includes("₹")) return `₹${Math.round(value).toLocaleString("en-IN")}`;
  return String(value);
}

export function AdviceSimulation({ userId, advice, onClose }: { userId: string; advice: string; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const derive = useMutation({ mutationFn: () => simulateAdvice(userId, advice) });
  const rerun = useMutation({ mutationFn: (request: SimulateRequest) => simulate(request) });
  const [targets, setTargets] = useState<Record<string, string>>({});
  const changes = derive.data?.changes ?? [];

  useEffect(() => {
    dialog.current?.showModal();
    derive.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const valueOf = (c: AdviceChange) =>
    Array.isArray(c.target) || targets[c.field] === undefined ? c.target : Number(targets[c.field]);
  const invalid = changes.some((c) => targets[c.field] !== undefined &&
    (targets[c.field] === "" || !Number.isFinite(Number(targets[c.field])) || Number(targets[c.field]) < 0));
  const edited = changes.some((c) => targets[c.field] !== undefined && Number(targets[c.field]) !== c.target);
  const profiles: { before: Profiles; after: Profiles } | undefined = rerun.data ?? derive.data;

  const runEdited = () => {
    const parts: Record<Twin, Record<string, unknown>> = { health: {}, finance: {}, insurance: {} };
    for (const c of changes) parts[c.domain][c.field] = valueOf(c);
    rerun.mutate({ user_id: userId, forecast_months: 1, ...parts } as SimulateRequest);
  };

  return createPortal(
    <dialog ref={dialog} onClose={onClose} onCancel={onClose} aria-labelledby="advice-simulation-title"
      className="m-auto max-h-[90vh] w-[min(94vw,640px)] overflow-y-auto rounded-lg border border-gold/30 bg-ink p-0 text-ivory shadow-2xl backdrop:bg-black/75">
      <div className="p-5 sm:p-6">
        <div className="flex items-center justify-between gap-3">
          <h2 id="advice-simulation-title" className="flex items-center gap-2 font-display text-xl font-semibold text-champagne">
            <FlaskConical className="h-5 w-5 text-gold" /> Simulate advice
          </h2>
          <button type="button" onClick={onClose} aria-label="Close simulation" title="Close" className="rounded p-2 text-taupe hover:text-ivory"><X className="h-4 w-4" /></button>
        </div>
        <p className="mt-3 break-words text-sm text-ivory/90">{advice.replace(/\*\*/g, "")}</p>

        {derive.isPending && <p className="mt-5 text-sm text-taupe">Applying this advice to your twin…</p>}
        {derive.isError && <p role="alert" className="mt-5 text-sm text-risk">{derive.error.message}</p>}

        {derive.data && changes.length === 0 && derive.data.already_met.length > 0 && (
          <p className="mt-5 rounded-md border border-good/30 px-3 py-2 text-sm text-ivory/90">
            Your twin already reflects this: {derive.data.already_met.map((c) => `${c.label} is ${display(c, c.current)}`).join(", ")}.
            Keep it up; there is no change to simulate.
          </p>
        )}

        {derive.data && changes.length === 0 && derive.data.already_met.length === 0 && (
          <p className="mt-5 rounded-md border border-gold/20 px-3 py-2 text-sm text-ivory/90">
            {/\b(maintain|keep|continue|stay)\w*/i.test(advice)
              ? "This advice is about keeping your current values, so your scores stay where they are. Simulate a change instead (for example losing weight or cutting salt) to see a difference."
              : "This advice doesn't change anything the twin calculates (for example a check-up, a test, or a habit the models don't take as an input). Follow it as expert guidance; your scores move once a measured value changes."}
          </p>
        )}

        {changes.length > 0 && (
          <section className="mt-5">
            <h3 className="text-sm font-semibold text-champagne">Changes taken from this advice</h3>
            <ul className="mt-2 divide-y divide-gold/10">
              {changes.map((c) => (
                <li key={c.field} className="py-2 text-sm">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-taupe">{c.label}</span>
                    <span className="flex items-center gap-2 font-mono">
                      <span className="text-ivory/70">{display(c, c.current)}</span>→
                      {Array.isArray(c.target) || BINARY.has(c.field) ? (
                        <span className="text-champagne">{display(c, c.target)}</span>
                      ) : (
                        <input type="number" min={0} step="any" aria-label={`Assumed ${c.label}`} disabled={rerun.isPending}
                          value={targets[c.field] ?? String(c.target)}
                          onChange={(e) => setTargets({ ...targets, [c.field]: e.target.value })}
                          className="w-28 rounded-md border border-gold/20 bg-ink px-2 py-1 text-right text-champagne" />
                      )}
                    </span>
                  </div>
                  <p className={`text-xs ${c.basis.startsWith("assumed") ? "text-warn" : "text-taupe"}`}>{c.basis}</p>
                </li>
              ))}
            </ul>
            {edited && (
              <button type="button" onClick={runEdited} disabled={invalid || rerun.isPending} className="btn-gold mt-3 px-4 py-2 text-sm disabled:opacity-50">
                <RefreshCcw className="h-4 w-4" /> {rerun.isPending ? "Recalculating…" : "Recalculate with my values"}
              </button>
            )}
            {rerun.isError && <p role="alert" className="mt-2 text-sm text-risk">{rerun.error.message}</p>}
          </section>
        )}

        {profiles && changes.length > 0 && (
          <section aria-live="polite" className="mt-5 border-t border-gold/20 pt-4">
            <h3 className="text-sm font-semibold text-champagne">If you follow this advice</h3>
            <table className="mt-2 w-full text-sm">
              <thead><tr className="text-left text-xs text-taupe"><th>Score</th><th className="text-right">Now</th><th className="text-right">With advice</th></tr></thead>
              <tbody>
                {([
                  ["Health", profiles.before.health.overall_health_score, profiles.after.health.overall_health_score],
                  ["Financial", profiles.before.finance.financial_stability_score, profiles.after.finance.financial_stability_score],
                  ["Insurance", profiles.before.insurance.insurance_adequacy_score, profiles.after.insurance.insurance_adequacy_score],
                ] as const).map(([label, before, after]) => (
                  <tr key={label} className="border-t border-gold/10">
                    <td className="py-2 text-taupe">{label}</td>
                    <td className="text-right font-mono">{before}</td>
                    <td className={`text-right font-mono ${after > before ? "text-good" : after < before ? "text-risk" : ""}`}>
                      {after} <span className="text-xs text-taupe">({after - before >= 0 ? "+" : ""}{after - before})</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!rerun.data && derive.data && derive.data.factor_impacts.length > 0 && (
              <ul className="mt-3 flex flex-col gap-1 text-xs">
                {derive.data.factor_impacts.map((f) => (
                  <li key={`${f.domain}-${f.label}`} className="flex flex-wrap justify-between gap-2">
                    <span className="text-taupe">{f.label}</span>
                    <span className="font-mono text-ivory/80">{String(f.before ?? "—")} → {String(f.after ?? "—")}{f.unit === "%" ? "%" : ""}</span>
                  </li>
                ))}
              </ul>
            )}
            <p className="mt-3 text-xs text-taupe">Assumes the advice is fully followed. Illustrative model comparison, not a timed forecast; nothing is saved.</p>
          </section>
        )}
      </div>
    </dialog>, document.body,
  );
}
