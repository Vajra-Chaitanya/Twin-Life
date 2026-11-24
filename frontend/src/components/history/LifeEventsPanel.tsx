import { Bot, CalendarClock, HandCoins, HeartPulse, Layers, Lock, MessageSquareText, ShieldCheck, Wallet, type LucideIcon } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { formatRelative } from "../../lib/format";
import { useLifeEvents } from "../../lib/queries";
import type { Commitment, Twin } from "../../lib/types";
import { ChangeTable } from "../advisor/TwinUpdateCard";
import { Panel } from "../dashboard/Panel";

export const TWINS: Record<Twin, { label: string; color: string; icon: LucideIcon }> = {
  health: { label: "Health", color: "#E0A899", icon: HeartPulse },
  finance: { label: "Finance", color: "#D4AF37", icon: Wallet },
  insurance: { label: "Insurance", color: "#C9CED6", icon: ShieldCheck },
};

function TwinBadge({ twin }: { twin: Twin }) {
  const { label, color, icon: Icon } = TWINS[twin];
  return (
    <span
      className="flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold tracking-wider uppercase"
      style={{ color, borderColor: `${color}55`, background: `${color}14` }}
    >
      <Icon className="h-3 w-3" /> {label}
    </span>
  );
}

function commitmentText(c: Commitment) {
  const amount = `₹${(c.principal ?? c.emi).toLocaleString("en-IN")}`;
  if (c.receivable) return `${c.lender} owes you ${amount}`;
  if (c.informal) return `Owe ${c.lender} ${amount} (no plan yet)`;
  return `${c.item} ₹${c.emi.toLocaleString("en-IN")}/mo ${c.end ? `until ${c.end}` : "(tenure unknown)"}`;
}

export function LifeEventsPanel({ userId, lockTo, className = "lg:col-span-3" }: { userId: string; lockTo?: Twin; className?: string }) {
  const events = useLifeEvents(userId);
  const [chosen, setFilter] = useState<Twin | "all">("all");
  const filter = lockTo ?? chosen;
  const list = events.data?.events ?? [];
  const counts = events.data?.counts;
  const commitments = events.data?.commitments ?? [];
  const shown = filter === "all" ? list : list.filter((e) => e.domains.includes(filter));

  return (
    <Panel
      title={lockTo ? `${TWINS[lockTo].label} timeline` : "Life events"}
      icon={CalendarClock}
      subtitle={lockTo ? `Everything you told the advisor that affects your ${lockTo} twin` : "Everything you told the advisor, across your health, finance and insurance twins"}
      className={className}
      action={
        list.some((e) => !e.undone) && (
          <Link to="/advisor" className="btn-ghost px-3 py-1.5 text-xs">
            <Bot className="h-3.5 w-3.5" /> Revert via advisor
          </Link>
        )
      }
    >
      {list.length > 0 && !lockTo && (
        <div role="radiogroup" aria-label="Filter by twin" className="mb-4 flex flex-wrap gap-2">
          {(["all", "health", "finance", "insurance"] as const).map((key) => {
            const active = filter === key;
            const twin = key === "all" ? null : TWINS[key];
            const Icon = twin?.icon ?? Layers;
            const count = key === "all" ? list.filter((e) => !e.undone).length : counts?.[key] ?? 0;
            return (
              <button
                key={key}
                type="button"
                role="radio"
                aria-checked={active}
                onClick={() => setFilter(key)}
                className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs transition-colors ${
                  active ? "bg-gold/15 text-champagne" : "text-taupe hover:text-champagne"
                }`}
                style={{ borderColor: active ? twin?.color ?? "#D4AF37" : "rgb(212 175 55 / 0.15)" }}
              >
                <Icon className="h-3.5 w-3.5" style={{ color: twin?.color ?? "#D4AF37" }} />
                {twin?.label ?? "All twins"}
                <span className="font-mono text-[10px] opacity-70">{count}</span>
              </button>
            );
          })}
        </div>
      )}

      {commitments.length > 0 && (filter === "all" || filter === "finance") && !lockTo && (
        <div className="mb-4 flex flex-wrap gap-2">
          {commitments.map((c, i) => (
            <span key={i} className="flex items-center gap-1.5 rounded-full border border-gold/25 bg-gold/5 px-3 py-1 text-xs text-champagne">
              {c.receivable || c.informal ? <HandCoins className="h-3 w-3 text-gold" /> : <Lock className="h-3 w-3 text-gold" />}
              {commitmentText(c)}
            </span>
          ))}
        </div>
      )}

      {list.length === 0 ? (
        <p className="flex items-center gap-2 text-sm text-taupe">
          <MessageSquareText className="h-4 w-4 text-gold" />
          Tell the <Link to="/advisor" className="text-champagne underline-offset-2 hover:underline">advisor</Link> what happened, e.g. “I bought a car
          for 8 lakh, EMI 15000 for 5 years”, “I had dengue”, “I took a term plan” or “I subscribed to Netflix for 649 a month”.
        </p>
      ) : shown.length === 0 ? (
        <p className="text-sm text-taupe">No {filter} events yet.</p>
      ) : (
        <ol className="relative flex flex-col gap-4 border-l border-gold/20 pl-5">
          {shown.map((e) => (
            <li key={e.id} className={e.undone ? "opacity-50" : ""}>
              <span
                className="absolute -left-[5px] mt-1.5 h-2.5 w-2.5 rounded-full"
                style={{ background: TWINS[e.domains[0]]?.color ?? "#D4AF37" }}
              />
              <div className="flex flex-wrap items-center gap-2 text-sm">
                {e.domains.map((d) => <TwinBadge key={d} twin={d} />)}
                <span className={e.undone ? "text-taupe line-through" : "text-ivory"}>{e.summary}</span>
                <span className="text-[11px] text-taupe">{formatRelative(e.created_at)}</span>
                {e.undone ? (
                  <span className="ml-auto text-[11px] text-taupe">Reverted</span>
                ) : (
                  <span className="ml-auto font-mono text-[10px] text-taupe" title='Ask the advisor e.g. "undo #id"'>#{e.id}</span>
                )}
              </div>
              {!e.undone && e.changes.length > 0 && (
                <div className="max-w-md">
                  <ChangeTable changes={e.changes} />
                </div>
              )}
              {!e.undone && e.log && <p className="mt-1 text-[11px] text-taupe">Logged in your history; it doesn't change your scores.</p>}
            </li>
          ))}
        </ol>
      )}
    </Panel>
  );
}
