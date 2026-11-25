import { motion } from "framer-motion";
import { ArrowRight, HelpCircle, History, RefreshCcw, Undo2 } from "lucide-react";
import type { ChatMessage, LifeEvent } from "../../lib/types";

// Metrics where a higher value is an improvement; everything else is better lower.
const HIGHER_IS_BETTER = new Set(["Health score", "Free cash / month", "Stability score", "Insurance score"]);
const MONEY = new Set(["Free cash / month", "Projected 5-yr medical cost"]);
const DOMAIN_LABELS = { health: "Health", finance: "Finance", insurance: "Insurance" } as const;

export function formatMetric(label: string, value: number | null) {
  if (value === null) return "—";
  if (MONEY.has(label)) return `₹${Math.round(value).toLocaleString("en-IN")}`;
  return label.endsWith("%") ? `${value}%` : String(value);
}

export function metricTone(label: string, before: number | null, after: number | null) {
  if (label === "CVD risk %" || label === "Diabetes risk %") return "text-ivory";
  if (before === null || after === null || before === after) return "text-ivory";
  return (after > before) === HIGHER_IS_BETTER.has(label) ? "text-good" : "text-risk";
}

function formatFactorValue(value: number | string | null, unit: string) {
  if (value === null) return "Not available";
  if (typeof value === "string") return value || "None recorded";
  if (unit === "%") return `${value}%`;
  if (unit === "ratio") return `${value.toFixed(2)}x`;
  if (unit === "kg/m2") return `${value.toFixed(1)} kg/m²`;
  if (unit.startsWith("INR")) {
    const suffix = unit === "INR" ? "" : `/${unit.slice(4)}`;
    return `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 2 })}${suffix}`;
  }
  if (unit === "points deducted") return `${value} points`;
  if (unit === "points") return `${value.toFixed(1)} points`;
  if (unit === "months") return `${value.toFixed(1)} months`;
  return `${value}${unit ? ` ${unit}` : ""}`;
}

export function ChangeTable({ changes }: { changes: LifeEvent["changes"] }) {
  return (
    <table className="mt-2 w-full text-sm">
      <tbody>
        {changes.map((c) => (
          <tr key={c.label} className="border-t border-gold/10 first:border-t-0">
            <td className="py-1 text-taupe">{c.label.replace(" %", "")}</td>
            <td className="py-1 text-right font-mono text-ivory/70">{formatMetric(c.label, c.before)}</td>
            <td className="w-6 py-1 text-center">
              <ArrowRight className="inline h-3 w-3 text-taupe" />
            </td>
            <td className={`py-1 text-right font-mono font-semibold ${metricTone(c.label, c.before, c.after)}`}>{formatMetric(c.label, c.after)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

type Props = {
  updates: LifeEvent[];
  reverted: NonNullable<ChatMessage["reverted"]>;
  pending: string[];
  undoneIds: Set<number>;
  onUndo: (event: LifeEvent) => void;
  undoing: boolean;
};

export function TwinUpdateCard({ updates, reverted, pending, undoneIds, onUndo, undoing }: Props) {
  if (updates.length === 0 && reverted.length === 0 && pending.length === 0) return null;
  // Events from one message share a single recompute, so the metric changes are shown once.
  const impacts = updates.flatMap((update) => update.health_impacts ?? []).filter((impact) =>
    impact.weight_percent === undefined || impact.before !== impact.after,
  );
  const factorImpacts = (updates[0]?.factor_impacts ?? []).filter((factor) => factor.status === "changed");
  const changedFactors = factorImpacts.length;
  const changes = (updates[0]?.changes ?? []).filter((change) =>
    !impacts.length || !["Health score", "CVD risk %", "Diabetes risk %"].includes(change.label),
  );
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-4 rounded-xl border border-gold/30 bg-gold/5 p-4"
      onClick={(e) => e.stopPropagation()}
    >
      {reverted.length > 0 && (
        <>
          <div className="flex items-center gap-2">
            <History className="h-4 w-4 text-gold" />
            <span className="text-xs font-semibold tracking-widest text-champagne uppercase">Reverted</span>
            <span className="text-xs text-taupe">· dashboard and history updated</span>
          </div>
          <ul className="mt-3 flex flex-col gap-1.5 text-sm text-ivory">
            {reverted.map((r) => (
              <li key={r.id} className="flex items-center gap-2">
                <Undo2 className="h-3.5 w-3.5 text-taupe" /> {r.summary}
              </li>
            ))}
          </ul>
          {reverted[0].changes.length > 0 && <ChangeTable changes={reverted[0].changes} />}
        </>
      )}
      {updates.length > 0 && (
        <div className={reverted.length > 0 ? "mt-3 border-t border-gold/10 pt-3" : ""}>
          <div className="flex items-center gap-2">
            <RefreshCcw className="h-4 w-4 text-gold" />
            <span className="text-xs font-semibold tracking-widest text-champagne uppercase">Twin updated</span>
            <span className="text-xs text-taupe">· recorded in your life timeline</span>
          </div>
          <ul className="mt-3 flex flex-col gap-1.5">
            {updates.map((u) => {
              const undone = u.undone || undoneIds.has(u.id);
              return (
                <li key={u.id} className="flex items-center gap-2 text-sm">
                  <span className={undone ? "text-taupe line-through" : "text-ivory"}>{u.summary}</span>
                  {u.commitment?.end && !undone && (
                    <span className="rounded-full border border-gold/20 px-2 py-0.5 text-[10px] text-champagne">until {u.commitment.end}</span>
                  )}
                  {undone ? (
                    <span className="ml-auto text-[11px] text-taupe">Reverted</span>
                  ) : (
                    <button
                      type="button"
                      disabled={undoing}
                      onClick={() => onUndo(u)}
                      title="Asks the advisor to revert this update"
                      className="ml-auto flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] text-taupe transition-colors hover:text-champagne disabled:opacity-50"
                    >
                      <Undo2 className="h-3 w-3" /> Undo
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
          {factorImpacts.length > 0 && (
            <details className="mt-3 border-t border-gold/10 pt-2">
              <summary className="cursor-pointer text-xs font-semibold text-champagne">
                All factors that changed across your twins ({changedFactors})
              </summary>
              <div className="mt-3 max-h-96 space-y-4 overflow-y-auto pr-1">
                {(["health", "finance", "insurance"] as const).map((domain) => {
                  const rows = factorImpacts.filter((factor) => factor.domain === domain);
                  if (rows.length === 0) return null;
                  return (
                    <section key={domain}>
                      <h4 className="mb-1 text-[11px] font-semibold tracking-wide text-taupe uppercase">{DOMAIN_LABELS[domain]}</h4>
                      <ul className="divide-y divide-gold/10">
                        {rows.map((factor) => (
                          <li key={`${factor.domain}-${factor.label}`} className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 py-1.5 text-xs">
                            <span className="text-ivory/80">{factor.label}</span>
                            <span className="flex flex-wrap items-center justify-end gap-x-2 font-mono">
                              <span className="text-ivory/70">{formatFactorValue(factor.before, factor.unit)} → {formatFactorValue(factor.after, factor.unit)}</span>
                              {factor.delta !== null && factor.status === "changed" && (
                                <span className="text-champagne">Δ {factor.delta > 0 ? "+" : ""}{formatFactorValue(factor.delta, factor.unit)}</span>
                              )}
                              <span className={factor.status === "changed" ? "text-champagne" : "text-taupe"}>{factor.status}</span>
                            </span>
                          </li>
                        ))}
                      </ul>
                    </section>
                  );
                })}
              </div>
            </details>
          )}
          {impacts.length > 0 && (
            <div className="mt-3 border-t border-gold/10 pt-2">
              {impacts.map((impact, index) => (
                <div key={`${impact.label}-${index}`} className="py-1 text-sm">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <span className="text-taupe">{impact.label}</span>
                    <span className="font-mono text-ivory">
                      {impact.before === null && impact.after === null ? "Not available" : (
                        <>{impact.before ?? "—"}{impact.label.includes("estimate") && impact.before !== null ? "%" : ""} → {impact.after ?? "—"}{impact.label.includes("estimate") && impact.after !== null ? "%" : ""}</>
                      )}
                    </span>
                  </div>
                  {impact.weight_percent !== undefined && (
                    <p className="text-xs text-ivory/70">
                      {impact.weight_percent}% of score · contribution {impact.before_weighted_points?.toFixed(2) ?? "—"} → {impact.after_weighted_points?.toFixed(2) ?? "—"} points
                    </p>
                  )}
                  <p className="text-xs text-taupe">{impact.note}</p>
                </div>
              ))}
              <p className="mt-2 text-xs text-taupe">The models do not calculate how long an event's effect will last.</p>
            </div>
          )}
          {changes.length > 0 && <ChangeTable changes={changes} />}
        </div>
      )}
      {pending.length > 0 && (
        <div className={updates.length + reverted.length > 0 ? "mt-3 border-t border-gold/10 pt-3" : ""}>
          <p className="flex items-center gap-2 text-xs font-semibold tracking-widest text-champagne uppercase">
            <HelpCircle className="h-4 w-4 text-gold" /> Need a detail to update your twin
          </p>
          <ul className="mt-2 flex flex-col gap-1 text-sm text-ivory/90">
            {pending.map((q) => (
              <li key={q}>{q}</li>
            ))}
          </ul>
        </div>
      )}
    </motion.div>
  );
}
