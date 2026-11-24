import { useSyncExternalStore } from "react";

export type TourStep = { path: string; title: string; body: string };

export const TOUR: TourStep[] = [
  { path: "/", title: "Meet TwinLife AI", body: "One agentic digital twin that unifies a person's health, finances and insurance, and explains every number it produces." },
  { path: "/onboard", title: "Calibrate the twin", body: "A 4-step calibration with a live readout computed by the same formulas as the backend. Personas fill synthetic data in one click." },
  { path: "/dashboard", title: "The command dashboard", body: "Scores from a trained Random Forest and deterministic formulas. The SHAP chart shows exactly which factors push cardiovascular risk up or down." },
  { path: "/simulate", title: "What-If Lab", body: "Fork the future: move a slider and the twin re-runs the model, the formulas and a Monte Carlo forecast. Try 'Job loss' or 'Lose 10 kg'." },
  { path: "/history", title: "Time Machine", body: "Every assessment is a snapshot. Generate a demo journey, then press play to watch the twin improve over six checkpoints." },
  { path: "/chat", title: "AI Advisor", body: "A LangGraph orchestrator routes the question, retrieves guidelines (RAG), lets a Gemini agent call tools autonomously, and cites its sources." },
  { path: "/alerts", title: "Proactive watchdog", body: "Each new assessment is compared with the last. Threshold crossings become alerts, without the user having to ask." },
];

let state = { active: false, step: 0 };
const listeners = new Set<() => void>();
const emit = () => listeners.forEach((l) => l());

export const tour = {
  start() {
    state = { active: true, step: 0 };
    emit();
  },
  stop() {
    state = { ...state, active: false };
    emit();
  },
  go(step: number) {
    state = { active: true, step: Math.max(0, Math.min(TOUR.length - 1, step)) };
    emit();
  },
};

export function useTour() {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l);
      return () => listeners.delete(l);
    },
    () => state,
  );
}
