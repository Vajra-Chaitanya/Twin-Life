import { motion } from "framer-motion";
import { ArrowRight, HelpCircle, History, RefreshCcw, Undo2 } from "lucide-react";
import type { ChatMessage, LifeEvent } from "../../lib/types";

// Metrics where a higher value is an improvement; everything else is better lower.
const HIGHER_IS_BETTER = new Set(["Health score", "Free cash / month", "Stability score", "Insurance score"]);
const MONEY = new Set(["Free cash / month", "Projected 5-yr medical cost"]);

export function formatMetric(label: string, value: number | null) {
  if (value === null) return "—";
  if (MONEY.has(label)) return `₹${Math.round(value).toLocaleString("en-IN")}`;
  return label.endsWith("%") ? `${value}%` : String(value);
}

export function metricTone(label: string, before: number | null, after: number | null) {
  if (before === null || after === null || before === after) return "text-ivory";
  return (after > before) === HIGHER_IS_BETTER.has(label) ? "text-good" : "text-risk";
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
  const changes = updates[0]?.changes ?? [];
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
