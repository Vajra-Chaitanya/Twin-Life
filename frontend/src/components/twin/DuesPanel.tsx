import { AlertTriangle, CalendarClock, CheckCircle2, Clock, HandCoins, ShieldAlert } from "lucide-react";
import { Panel } from "../dashboard/Panel";
import { useDues } from "../../lib/queries";
import type { Due, DueStatus, Twin } from "../../lib/types";

const STATUS: Record<DueStatus, { label: string; className: string }> = {
  overdue: { label: "Overdue", className: "border-risk/40 bg-risk/10 text-risk" },
  expired: { label: "Expired", className: "border-risk/40 bg-risk/10 text-risk" },
  missing: { label: "Missing", className: "border-risk/40 bg-risk/10 text-risk" },
  outstanding: { label: "Outstanding", className: "border-warn/40 bg-warn/10 text-warn" },
  due_soon: { label: "Due soon", className: "border-warn/40 bg-warn/10 text-warn" },
  upcoming: { label: "Upcoming", className: "border-good/30 bg-good/5 text-good" },
};

const KIND_ICON = { instalment: Clock, debt: HandCoins, receivable: HandCoins, renewal: CalendarClock, missing_policy: ShieldAlert };

function DueRow({ due }: { due: Due }) {
  const Icon = KIND_ICON[due.kind];
  const status = STATUS[due.status];
  return (
    <li className="flex items-start gap-3 rounded-xl border border-gold/10 bg-ink/40 p-3">
      <Icon className="mt-0.5 h-4 w-4 shrink-0 text-gold" />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-ivory">{due.title}</span>
          <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase ${status.className}`}>{status.label}</span>
        </div>
        <p className="mt-0.5 text-[11px] text-taupe">{due.detail}</p>
      </div>
      <div className="shrink-0 text-right">
        {due.amount > 0 && <p className="font-mono text-sm text-champagne">₹{Math.round(due.amount).toLocaleString("en-IN")}</p>}
        {due.due_date && <p className="font-mono text-[10px] text-taupe">{due.due_date}</p>}
      </div>
    </li>
  );
}

export function DuesPanel({ userId, domain, title, className }: { userId: string; domain: Twin; title: string; className?: string }) {
  const dues = useDues(userId);
  const items = (dues.data?.dues ?? []).filter((d) => d.domain === domain);
  const attention = items.filter((d) => !["upcoming", "due_soon"].includes(d.status)).length;
  return (
    <Panel
      title={title}
      icon={attention ? AlertTriangle : CalendarClock}
      accent={attention ? "text-risk" : undefined}
      subtitle={attention ? `${attention} item${attention === 1 ? "" : "s"} need attention (also sent to Alerts)` : "Scheduled from what you told the advisor"}
      className={className}
    >
      {dues.isPending ? (
        <div className="h-24 animate-pulse rounded-xl bg-gold/5" />
      ) : items.length === 0 ? (
        <p className="flex items-center gap-2 text-sm text-taupe">
          <CheckCircle2 className="h-4 w-4 text-good" /> Nothing due. Tell this twin's chat about loans, EMIs, lending or policies to track them here.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {items.map((d) => (
            <DueRow key={`${d.kind}-${d.title}-${d.due_date}`} due={d} />
          ))}
        </ul>
      )}
    </Panel>
  );
}
