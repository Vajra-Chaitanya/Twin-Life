import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, Bell, BellOff, CheckCheck, HeartPulse, Info, ShieldCheck, Wallet } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { formatRelative } from "../lib/format";
import { useMarkRead, useNotifications } from "../lib/notifications";
import type { Notification } from "../lib/types";
import { useCurrentUser } from "../lib/user";

const TYPE_META: Record<string, { label: string; icon: typeof Bell; accent: string }> = {
  baseline: { label: "Baseline recorded", icon: Info, accent: "text-insurance" },
  health_score_drop: { label: "Health score drop", icon: HeartPulse, accent: "text-health" },
  dti_high: { label: "Debt load rising", icon: Wallet, accent: "text-finance" },
  low_savings_rate: { label: "Low savings rate", icon: Wallet, accent: "text-finance" },
  insurance_score_drop: { label: "Insurance score drop", icon: ShieldCheck, accent: "text-insurance" },
  new_rider_gap: { label: "New rider gap", icon: ShieldCheck, accent: "text-insurance" },
  due_overdue: { label: "Payment overdue", icon: AlertTriangle, accent: "text-risk" },
  due_outstanding: { label: "Outstanding dues", icon: Wallet, accent: "text-warn" },
  due_due_soon: { label: "Payment due soon", icon: Wallet, accent: "text-finance" },
  due_expired: { label: "Policy expired", icon: ShieldCheck, accent: "text-risk" },
  due_missing: { label: "Policy missing", icon: ShieldCheck, accent: "text-risk" },
};

const FILTERS = ["all", "unread", "warning"] as const;

function AlertCard({ n, onRead, index }: { n: Notification; onRead: () => void; index: number }) {
  const meta = TYPE_META[n.type] ?? { label: n.type, icon: Bell, accent: "text-gold" };
  const Icon = meta.icon;
  const warning = n.severity === "warning" && !n.historical;
  return (
    <motion.li
      layout
      initial={{ opacity: 0, x: -16 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 16 }}
      transition={{ delay: Math.min(index, 10) * 0.04 }}
      className="relative pl-10"
    >
      <span
        className={`absolute top-5 left-0 flex h-8 w-8 items-center justify-center rounded-full border bg-ink ${
          warning ? "border-warn/50" : "border-insurance/40"
        }`}
      >
        {!n.read && warning && <span className="absolute inset-0 animate-ping rounded-full border border-warn/40" />}
        <Icon className={`h-4 w-4 ${meta.accent}`} />
      </span>
      <button
        type="button"
        onClick={onRead}
        disabled={n.read}
        className={`glass w-full p-4 text-left transition-colors ${n.read ? "opacity-60" : "hover:border-gold/40"}`}
      >
        <div className="flex items-center gap-2 text-xs">
          <span className={`font-semibold tracking-wide uppercase ${warning ? "text-warn" : "text-insurance"}`}>{n.historical ? "Earlier renewal alert" : meta.label}</span>
          {!n.read && <span className="h-1.5 w-1.5 rounded-full bg-gold" aria-label="unread" />}
          <span className="ml-auto text-taupe">
            {n.snapshot_id !== null ? `snapshot #${n.snapshot_id}` : n.domain ? (
              <Link to={`/twin/${n.domain}`} onClick={(e) => e.stopPropagation()} className="text-champagne hover:underline">
                Open {n.domain === "finance" ? "Financial" : n.domain[0].toUpperCase() + n.domain.slice(1)} Twin
              </Link>
            ) : ""}{" "}
            · {formatRelative(n.created_at)}
          </span>
        </div>
        <p className="mt-2 text-sm leading-relaxed text-ivory/90">{n.message}</p>
        {!n.read && <p className="mt-2 text-[11px] text-taupe/70">Click to mark as read</p>}
      </button>
    </motion.li>
  );
}

export function Alerts() {
  const userId = useCurrentUser();
  const feed = useNotifications(userId);
  const markRead = useMarkRead(userId);
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("all");

  if (!userId) {
    return (
      <div className="glass mx-auto mt-10 max-w-xl p-10 text-center">
        <Bell className="mx-auto h-12 w-12 text-gold" />
        <h2 className="mt-5 font-display text-2xl font-semibold text-metal">No twin to watch yet</h2>
        <Link to="/onboard" className="btn-gold mt-8">Calibrate twin</Link>
      </div>
    );
  }

  const items = (feed.data?.notifications ?? []).filter((n) =>
    filter === "unread" ? !n.read : filter === "warning" ? n.severity === "warning" && !n.historical : true,
  );

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-5">
      <div className="glass flex flex-wrap items-center gap-4 p-5">
        <motion.div
          className="flex h-12 w-12 items-center justify-center rounded-2xl border border-gold/30 bg-gold/10"
          animate={{ boxShadow: ["0 0 0 rgb(212 175 55 / 0)", "0 0 24px rgb(212 175 55 / 0.45)", "0 0 0 rgb(212 175 55 / 0)"] }}
          transition={{ duration: 3, repeat: Infinity }}
        >
          <Bell className="h-5 w-5 text-gold" />
        </motion.div>
        <div className="flex-1">
          <h2 className="font-display text-lg font-semibold text-ivory">Watchdog agent</h2>
          <p className="text-xs text-taupe">
            Compares every new assessment with the previous one: health drop &gt;10, DTI &gt;40%, savings &lt;10%, insurance drop &gt;15, new rider gaps.
          </p>
        </div>
        <button
          type="button"
          onClick={() => markRead.mutate(undefined)}
          disabled={!feed.data?.unread || markRead.isPending}
          className="btn-ghost px-3 py-1.5 text-xs disabled:opacity-40"
        >
          <CheckCheck className="h-3.5 w-3.5" /> Mark all read
        </button>
      </div>

      <div role="tablist" aria-label="Filter alerts" className="flex gap-2">
        {FILTERS.map((f) => (
          <button
            key={f}
            type="button"
            role="tab"
            aria-selected={filter === f}
            onClick={() => setFilter(f)}
            className={`rounded-full border px-3 py-1 text-xs capitalize transition-colors ${
              filter === f ? "border-gold bg-gold/15 text-champagne" : "border-gold/15 text-taupe hover:border-gold/40"
            }`}
          >
            {f}
            {f === "unread" && feed.data ? ` (${feed.data.unread})` : ""}
          </button>
        ))}
      </div>

      {feed.isPending && <div className="glass h-40 animate-pulse" />}
      {feed.isError && (
        <p className="flex items-center gap-2 rounded-xl border border-risk/40 bg-risk/10 px-4 py-2 text-sm text-risk">
          <AlertTriangle className="h-4 w-4" /> Could not load alerts.
        </p>
      )}
      {feed.data && items.length === 0 && (
        <div className="glass flex flex-col items-center gap-3 p-10 text-center text-taupe">
          <BellOff className="h-8 w-8 text-gold/60" />
          {filter === "all" ? "No alerts yet. Run an assessment to start monitoring." : "Nothing here."}
        </div>
      )}

      <ol className="relative flex flex-col gap-3">
        <span className="absolute top-4 bottom-4 left-[15px] w-px bg-gradient-to-b from-gold/40 via-gold/15 to-transparent" aria-hidden />
        <AnimatePresence initial={false}>
          {items.map((n, i) => (
            <AlertCard key={n.id} n={n} index={i} onRead={() => markRead.mutate([n.id])} />
          ))}
        </AnimatePresence>
      </ol>
    </div>
  );
}
