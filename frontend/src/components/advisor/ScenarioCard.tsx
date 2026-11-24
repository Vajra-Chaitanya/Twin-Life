import { motion } from "framer-motion";
import { ArrowRight, Calculator } from "lucide-react";
import type { Scenario } from "../../lib/types";

const VERDICT: Record<string, { label: string; className: string }> = {
  comfortable: { label: "Comfortable", className: "border-good/40 bg-good/10 text-good" },
  stretch: { label: "A stretch", className: "border-warn/40 bg-warn/10 text-warn" },
  risky: { label: "Risky", className: "border-risk/40 bg-risk/10 text-risk" },
  improves: { label: "Improves", className: "border-good/40 bg-good/10 text-good" },
  worsens: { label: "Worsens", className: "border-risk/40 bg-risk/10 text-risk" },
};

export function ScenarioCard({ scenario }: { scenario: Scenario }) {
  const verdict = VERDICT[scenario.verdict] ?? { label: scenario.verdict, className: "border-gold/30 text-champagne" };
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-4 rounded-xl border border-gold/20 bg-ink/50 p-4"
      onClick={(e) => e.stopPropagation()}
    >
      <div className="flex flex-wrap items-center gap-2">
        <Calculator className="h-4 w-4 text-gold" />
        <span className="text-xs font-semibold tracking-widest text-champagne uppercase">Computed impact</span>
        <span className="text-xs text-taupe">· {scenario.headline}</span>
        <span className={`ml-auto rounded-full border px-2.5 py-0.5 text-xs font-semibold ${verdict.className}`}>{verdict.label}</span>
      </div>

      {scenario.metrics.length > 0 ? (
        <table className="mt-3 w-full text-sm">
          <tbody>
            {scenario.metrics.map((m) => (
              <tr key={m.label} className="border-t border-gold/10 first:border-t-0">
                <td className="py-1.5 text-taupe">{m.label}</td>
                <td className="py-1.5 text-right font-mono text-ivory/70">{m.before}</td>
                <td className="w-6 py-1.5 text-center">
                  <ArrowRight className="inline h-3 w-3 text-taupe" />
                </td>
                <td
                  className={`py-1.5 text-right font-mono font-semibold ${
                    m.better === null || m.before === m.after ? "text-ivory" : m.better ? "text-good" : "text-risk"
                  }`}
                >
                  {m.after}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <ul className="mt-3 flex flex-col gap-1 text-sm text-ivory/90">
          {scenario.facts.map((f) => (
            <li key={f}>{f}</li>
          ))}
        </ul>
      )}
      {scenario.assumptions.length > 0 && <p className="mt-2 text-[11px] text-taupe/70">Assumes: {scenario.assumptions.join(" ")}</p>}
    </motion.div>
  );
}
