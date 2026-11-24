import { Bike, Car, HeartPulse, Home, Landmark, Plane, ShieldCheck, Smartphone, Umbrella, type LucideIcon } from "lucide-react";
import { InsurancePanelBody } from "../components/dashboard/InsurancePanel";
import { Panel } from "../components/dashboard/Panel";
import { LifeEventsPanel } from "../components/history/LifeEventsPanel";
import { DuesPanel } from "../components/twin/DuesPanel";
import { TwinPage } from "../components/twin/TwinPage";
import { ScoreRing } from "../components/ui/ScoreRing";
import type { Policy } from "../lib/types";

const inr = (n: number) => `₹${Math.round(n).toLocaleString("en-IN")}`;

function policyIcon(p: Policy): LucideIcon {
  if (p.type === "vehicle") return /bike|scooter|two|motor/i.test(p.name) ? Bike : Car;
  return { life: Landmark, home: Home, travel: Plane, gadget: Smartphone, health_topup: HeartPulse, other: Umbrella }[p.type] ?? Umbrella;
}

export function InsuranceTwin() {
  return (
    <TwinPage domain="insurance" intro="Health cover and riders, plus vehicle, life, home, travel and other policies with renewals.">
      {({ userId, snapshot, inputs }) => {
        const i = snapshot.insurance;
        const ii = inputs?.insurance_inputs;
        const portfolio = i.portfolio;
        const policies = portfolio?.policies ?? ii?.policies ?? [];
        const today = new Date().toISOString().slice(0, 10);
        return (
          <>
            <Panel title="Insurance adequacy" icon={ShieldCheck} accent="text-insurance" subtitle="Health cover vs projected costs and rider gaps">
              <div className="flex flex-col items-center gap-4">
                <ScoreRing value={i.insurance_adequacy_score} label="Adequacy" color="#C9CED6" />
                {portfolio && (
                  <p className="text-center text-xs text-taupe">
                    Total premiums {inr(portfolio.total_annual_premium)}/yr across {policies.length + (portfolio.health_cover > 0 ? 1 : 0)} polic
                    {policies.length + (portfolio.health_cover > 0 ? 1 : 0) === 1 ? "y" : "ies"}
                  </p>
                )}
              </div>
            </Panel>

            <Panel title="All policies" icon={Umbrella} accent="text-insurance" subtitle="Health and every other cover you hold">
              <ul className="flex flex-col gap-2">
                {ii && ii.sum_insured > 0 && (
                  <li className="flex items-center gap-3 rounded-xl border border-gold/10 bg-ink/40 px-3 py-2.5 text-sm">
                    <HeartPulse className="h-4 w-4 text-health" />
                    <span className="flex-1 text-ivory">Health insurance</span>
                    <span className="font-mono text-xs text-taupe">cover {inr(ii.sum_insured)} · {inr(ii.annual_premium)}/yr</span>
                  </li>
                )}
                {policies.map((p, idx) => {
                  const Icon = policyIcon(p);
                  const expired = p.renewal_date !== null && p.renewal_date < today;
                  return (
                    <li key={`${p.name}-${idx}`} className="flex items-center gap-3 rounded-xl border border-gold/10 bg-ink/40 px-3 py-2.5 text-sm">
                      <Icon className="h-4 w-4 text-insurance" />
                      <span className="flex-1 text-ivory">{p.name}</span>
                      <span className="font-mono text-xs text-taupe">
                        {p.cover ? `cover ${inr(p.cover)} · ` : ""}
                        {p.premium ? `${inr(p.premium)}/yr · ` : ""}
                        <span className={expired ? "text-risk" : ""}>{expired ? "expired " : "renews "}{p.renewal_date ?? "?"}</span>
                      </span>
                    </li>
                  );
                })}
                {policies.length === 0 && (
                  <li className="text-sm text-taupe">No other policies yet. Try "I took bike insurance for 2500 a year" or "I bought a term plan of 1 crore".</li>
                )}
              </ul>
              {portfolio && portfolio.life_cover_gap > 0 && (
                <p className="mt-3 rounded-xl border border-warn/30 bg-warn/5 px-3 py-2 text-xs text-warn">
                  Life cover {inr(portfolio.life_cover)} vs ~{inr(portfolio.life_cover_recommended)} suggested (10× annual income).
                </p>
              )}
            </Panel>

            <DuesPanel userId={userId} domain="insurance" title="Renewals & gaps" className="lg:col-span-2" />

            <Panel title="Health cover analysis" icon={ShieldCheck} accent="text-insurance" className="lg:col-span-2">
              <InsurancePanelBody insurance={i} />
              <p className="mt-6 text-[11px] text-taupe/70">{i.disclaimer}</p>
            </Panel>
            <LifeEventsPanel userId={userId} lockTo="insurance" className="lg:col-span-2" />
          </>
        );
      }}
    </TwinPage>
  );
}
