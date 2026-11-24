import {
  Bell,
  FlaskConical,
  HeartPulse,
  History,
  LayoutDashboard,
  MessagesSquare,
  ScanLine,
  ShieldCheck,
  Wallet,
  type LucideIcon,
} from "lucide-react";

export type NavItem = {
  path: string;
  label: string;
  icon: LucideIcon;
  phase: number;
  blurb: string;
};

export const NAV_ITEMS: NavItem[] = [
  { path: "/dashboard", label: "Dashboard", icon: LayoutDashboard, phase: 4, blurb: "Live scores, SHAP explanations and twin vitals." },
  { path: "/twin/health", label: "Health Twin", icon: HeartPulse, phase: 4, blurb: "Heart and diabetes models, conditions, episodes and a health-only chat." },
  { path: "/twin/finance", label: "Financial Twin", icon: Wallet, phase: 4, blurb: "Cash flow, commitments, dues, subscriptions and a finance-only chat." },
  { path: "/twin/insurance", label: "Insurance Twin", icon: ShieldCheck, phase: 4, blurb: "Every policy, renewals, rider gaps and an insurance-only chat." },
  { path: "/onboard", label: "Calibrate Twin", icon: ScanLine, phase: 3, blurb: "Multi-step calibration with live health and finance feedback." },
  { path: "/simulate", label: "What-If Lab", icon: FlaskConical, phase: 6, blurb: "Parallel timelines: compare today with a simulated future." },
  { path: "/chat", label: "AI Advisor", icon: MessagesSquare, phase: 7, blurb: "Grounded answers with citations and an agent decision trace." },
  { path: "/history", label: "Time Machine", icon: History, phase: 5, blurb: "Scrub through past snapshots and watch your twin evolve." },
  { path: "/alerts", label: "Alerts", icon: Bell, phase: 8, blurb: "Proactive monitoring alerts from the watchdog agent." },
];
