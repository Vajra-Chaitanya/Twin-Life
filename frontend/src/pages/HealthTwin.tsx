import { Activity, Cigarette, Dumbbell, HeartPulse, Stethoscope, Wine } from "lucide-react";
import { CardioRiskPanel, DiabetesRiskPanel, RiskExplainPanel, Vital } from "../components/dashboard/HealthRiskPanels";
import { Panel } from "../components/dashboard/Panel";
import { LifeEventsPanel } from "../components/history/LifeEventsPanel";
import { TwinPage } from "../components/twin/TwinPage";
import { ScoreRing } from "../components/ui/ScoreRing";
import type { Tone } from "../lib/formulas";

const habitTone = (bad: boolean): Tone => (bad ? "risk" : "good");

export function HealthTwin() {
  return (
    <TwinPage domain="health" intro="Heart and diabetes models, vitals, conditions, habits and every health event you reported.">
      {({ userId, snapshot, inputs }) => {
        const h = snapshot.health;
        const hi = inputs?.health_inputs;
        const conditions = h.conditions ?? [];
        return (
          <>
            <Panel title="Health score" icon={HeartPulse} accent="text-health" subtitle="Composite of BMI, BP, model risks and diagnoses">
              <div className="flex flex-col items-center gap-4">
                <ScoreRing value={h.overall_health_score} label="Health" color="#E0A899" />
                {Boolean(h.condition_penalty) && (
                  <p className="text-center text-[11px] text-taupe">
                    Includes −{h.condition_penalty} for recorded conditions.
                  </p>
                )}
              </div>
            </Panel>

            <Panel title="Conditions & habits" icon={Stethoscope} accent="text-health" subtitle="From calibration and what you told the advisor">
              <div className="flex flex-wrap gap-2">
                {conditions.length === 0 ? (
                  <span className="text-sm text-taupe">No diagnosed conditions recorded.</span>
                ) : (
                  conditions.map((c) => (
                    <span key={c} className="rounded-full border border-risk/40 bg-risk/10 px-3 py-1 text-xs text-risk capitalize">
                      {c.replace(/_/g, " ")}
                    </span>
                  ))
                )}
              </div>
              {hi && (
                <div className="mt-4 grid grid-cols-2 gap-2">
                  <Vital label="Smoking" value={hi.smoke ? "Smoker" : "Non-smoker"} tone={habitTone(Boolean(hi.smoke))} />
                  <Vital label="Alcohol" value={hi.alco ? "Drinks" : "No"} tone={habitTone(Boolean(hi.alco))} />
                  <Vital label="Activity" value={hi.active ? "Active" : "Inactive"} tone={habitTone(!hi.active)} />
                  <Vital label="BP reading" value={`${hi.ap_hi}/${hi.ap_lo}`} tone={hi.ap_hi >= 140 ? "risk" : hi.ap_hi >= 120 ? "warn" : "good"} />
                  <Vital label="Weight" value={`${hi.weight_kg} kg`} tone="good" />
                  <Vital label="Fasting glucose" value={`${hi.blood_glucose_level} mg/dL`} tone={hi.blood_glucose_level >= 126 ? "risk" : hi.blood_glucose_level >= 100 ? "warn" : "good"} />
                </div>
              )}
              <div className="mt-3 flex gap-3 text-taupe">
                <Cigarette className="h-4 w-4" /> <Wine className="h-4 w-4" /> <Dumbbell className="h-4 w-4" /> <Activity className="h-4 w-4" />
              </div>
            </Panel>

            <CardioRiskPanel h={h} />
            <DiabetesRiskPanel h={h} />
            <RiskExplainPanel h={h} className="lg:col-span-2" />
            <LifeEventsPanel userId={userId} lockTo="health" className="lg:col-span-2" />
          </>
        );
      }}
    </TwinPage>
  );
}
