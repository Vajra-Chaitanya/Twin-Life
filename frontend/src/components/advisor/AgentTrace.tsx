import { motion } from "framer-motion";
import { BookOpen, Brain, GitBranch, HeartPulse, MessageSquareText, ShieldCheck, Wallet, Wrench } from "lucide-react";
import type { ChatMessage, ToolCall } from "../../lib/types";

const STEPS: Record<string, { label: string; detail: string; icon: typeof Brain }> = {
  route: { label: "Router", detail: "Keyword + LLM routing", icon: GitBranch },
  health: { label: "Health twin", detail: "Random Forest + SHAP", icon: HeartPulse },
  finance: { label: "Finance twin", detail: "Deterministic formulas", icon: Wallet },
  insurance: { label: "Insurance twin", detail: "Coverage & rider rules", icon: ShieldCheck },
  rag: { label: "Guideline RAG", detail: "MiniLM + ChromaDB", icon: BookOpen },
  simulate: { label: "Treatment agent", detail: "Gemini tool calling", icon: Wrench },
  narrate: { label: "Narrator", detail: "Gemini explanation", icon: MessageSquareText },
};

const TOOL_LABELS: Record<string, string> = {
  check_affordability: "Check affordability",
  check_insurance_coverage: "Check insurance coverage",
  get_cheaper_alternative: "Find cheaper alternative",
  get_health_context: "Read health context",
};

function compact(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return Number.isInteger(value) ? value.toLocaleString("en-IN") : value.toFixed(2);
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function ToolCard({ call, index }: { call: ToolCall; index: number }) {
  const entries = Object.entries(call.result ?? {}).filter(([, v]) => typeof v !== "object" || v === null).slice(0, 4);
  return (
    <motion.li
      initial={{ opacity: 0, x: 12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.9 + index * 0.25 }}
      className="rounded-xl border border-gold/15 bg-ink/50 p-3"
    >
      <p className="flex items-center gap-2 text-xs font-semibold text-champagne">
        <Wrench className="h-3 w-3 text-gold" />
        {TOOL_LABELS[call.tool] ?? call.tool}
      </p>
      <p className="mt-1 font-mono text-[11px] break-all text-taupe">
        in: {Object.entries(call.input ?? {}).map(([k, v]) => `${k}=${compact(v)}`).join(", ") || "—"}
      </p>
      {entries.length > 0 && (
        <dl className="mt-1.5 grid grid-cols-[auto_1fr] gap-x-2 gap-y-0.5 font-mono text-[11px]">
          {entries.map(([k, v]) => (
            <div key={k} className="contents">
              <dt className="text-taupe">{k}</dt>
              <dd className="truncate text-ivory/90">{compact(v)}</dd>
            </div>
          ))}
        </dl>
      )}
    </motion.li>
  );
}

export function AgentTrace({ message, pending }: { message: ChatMessage | null; pending: boolean }) {
  const steps = message?.pipeline ?? [];
  const simulation = message?.simulation && "tool_trace" in message.simulation ? message.simulation : null;

  return (
    <aside className="glass sticky top-6 flex max-h-[calc(100vh-8rem)] flex-col overflow-hidden p-5">
      <h2 className="flex items-center gap-2 font-display text-sm font-semibold tracking-[0.18em] text-champagne uppercase">
        <Brain className="h-4 w-4 text-gold" /> Agent trace
      </h2>
      <p className="mt-1 text-xs text-taupe">How the orchestrator answered the selected question.</p>

      <div className="mt-5 flex-1 overflow-y-auto pr-1">
        {pending && (
          <div className="flex flex-col gap-3">
            {["route", "health", "rag", "narrate"].map((key, i) => {
              const Icon = STEPS[key].icon;
              return (
                <motion.div
                  key={key}
                  className="flex items-center gap-3 text-sm text-taupe"
                  animate={{ opacity: [0.3, 1, 0.3] }}
                  transition={{ duration: 1.6, repeat: Infinity, delay: i * 0.4 }}
                >
                  <Icon className="h-4 w-4 text-gold" /> {STEPS[key].label}…
                </motion.div>
              );
            })}
          </div>
        )}

        {!pending && !message && <p className="text-sm text-taupe/70">Ask a question to see the reasoning pipeline.</p>}

        {!pending && message && (
          <>
            <ol className="relative flex flex-col gap-4">
              <span className="absolute top-2 bottom-2 left-[15px] w-px bg-gold/15" aria-hidden />
              {steps.map((key, i) => {
                const step = STEPS[key] ?? { label: key, detail: "", icon: Brain };
                const Icon = step.icon;
                return (
                  <motion.li
                    key={`${message.chat_id}-${key}`}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.12 }}
                    className="relative flex items-start gap-3"
                  >
                    <motion.span
                      className="relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-gold/50 bg-ink"
                      initial={{ boxShadow: "0 0 0 rgb(212 175 55 / 0)" }}
                      animate={{ boxShadow: ["0 0 0 rgb(212 175 55 / 0)", "0 0 18px rgb(212 175 55 / 0.7)", "0 0 6px rgb(212 175 55 / 0.3)"] }}
                      transition={{ delay: i * 0.12, duration: 0.8 }}
                    >
                      <Icon className="h-4 w-4 text-gold" />
                    </motion.span>
                    <div>
                      <p className="text-sm font-medium text-ivory">{step.label}</p>
                      <p className="text-[11px] text-taupe">
                        {key === "route" && message.routing.twins
                          ? `→ ${message.routing.twins.join(", ")} (${message.routing.mode})`
                          : key === "rag"
                            ? `${message.citations.length} guideline chunks`
                            : key === "simulate" && simulation
                              ? `${simulation.tool_trace.length} tool calls · ${simulation.iterations} iterations`
                              : step.detail}
                      </p>
                    </div>
                  </motion.li>
                );
              })}
            </ol>

            {simulation && simulation.tool_trace.length > 0 && (
              <div className="mt-6">
                <h3 className="mb-3 text-xs font-semibold tracking-widest text-champagne uppercase">Autonomous tool calls</h3>
                <ol className="flex flex-col gap-2">
                  {simulation.tool_trace.map((call, i) => (
                    <ToolCard key={i} call={call} index={i} />
                  ))}
                </ol>
              </div>
            )}
          </>
        )}
      </div>
    </aside>
  );
}
