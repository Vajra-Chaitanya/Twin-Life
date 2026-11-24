import { Lock, Repeat, Wallet } from "lucide-react";
import { FinancePanelBody } from "../components/dashboard/FinancePanel";
import { Panel } from "../components/dashboard/Panel";
import { LifeEventsPanel } from "../components/history/LifeEventsPanel";
import { DuesPanel } from "../components/twin/DuesPanel";
import { TwinPage } from "../components/twin/TwinPage";
import { ScoreRing } from "../components/ui/ScoreRing";
import { useLifeEvents } from "../lib/queries";

function SubscriptionsPanel({ userId }: { userId: string }) {
  const events = useLifeEvents(userId).data?.events ?? [];
  // Newest first: the latest start/cancel for each subscription decides whether it is still running.
  const latest = new Map<string, { active: boolean; summary: string; amount: number }>();
  for (const e of events) {
    if (e.type !== "subscription" || e.undone) continue;
    const m = e.summary.match(/^(Started|Cancelled) (.+?) \(₹([\d,]+)\/month\)/);
    if (!m || latest.has(m[2])) continue;
    latest.set(m[2], { active: m[1] === "Started", summary: e.summary, amount: Number(m[3].replace(/,/g, "")) });
  }
  const active = [...latest.entries()].filter(([, v]) => v.active);
  const total = active.reduce((s, [, v]) => s + v.amount, 0);
  return (
    <Panel title="Subscriptions" icon={Repeat} accent="text-finance" subtitle={active.length ? `₹${total.toLocaleString("en-IN")}/month in total` : "Recurring services you told the advisor about"}>
      {active.length === 0 ? (
        <p className="text-sm text-taupe">None recorded. Try "I subscribed to Netflix for 649 a month".</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {active.map(([name, v]) => (
            <li key={name} className="flex items-center justify-between rounded-xl border border-gold/10 bg-ink/40 px-3 py-2 text-sm">
              <span className="text-ivory capitalize">{name}</span>
              <span className="font-mono text-champagne">₹{v.amount.toLocaleString("en-IN")}/mo</span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

export function FinanceTwin() {
  return (
    <TwinPage domain="finance" intro="Cash flow, savings, loans, money you owe or lent, subscriptions and every payment due.">
      {({ userId, snapshot, inputs }) => {
        const f = snapshot.finance;
        const fi = inputs?.finance_inputs;
        return (
          <>
            <Panel title="Financial stability" icon={Wallet} accent="text-finance" subtitle="DTI, savings rate and emergency fund">
              <div className="flex flex-col items-center gap-4">
                <ScoreRing value={f.financial_stability_score} label="Stability" color="#D4AF37" />
                {fi && (
                  <p className="text-center text-xs text-taupe">
                    EMIs ₹{fi.emis.toLocaleString("en-IN")}/mo · fixed ₹{fi.fixed_expenses.toLocaleString("en-IN")} · variable ₹
                    {fi.variable_expenses.toLocaleString("en-IN")}
                  </p>
                )}
              </div>
            </Panel>
            <DuesPanel userId={userId} domain="finance" title="Commitments & dues" />
            <Panel title="Cash flow" icon={Lock} accent="text-finance" className="lg:col-span-2">
              <FinancePanelBody finance={f} />
            </Panel>
            <SubscriptionsPanel userId={userId} />
            <LifeEventsPanel userId={userId} lockTo="finance" className="lg:col-span-1" />
          </>
        );
      }}
    </TwinPage>
  );
}
