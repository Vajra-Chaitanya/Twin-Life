import {
  Bell,
  FlaskConical,
  History,
  LayoutDashboard,
  MessagesSquare,
  ScanLine,
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
  { path: "/onboard", label: "Calibrate Twin", icon: ScanLine, phase: 3, blurb: "Multi-step calibration with live health and finance feedback." },
  { path: "/simulate", label: "What-If Lab", icon: FlaskConical, phase: 6, blurb: "Parallel timelines: compare today with a simulated future." },
  { path: "/chat", label: "AI Advisor", icon: MessagesSquare, phase: 7, blurb: "Grounded answers with citations and an agent decision trace." },
  { path: "/history", label: "Time Machine", icon: History, phase: 5, blurb: "Scrub through past snapshots and watch your twin evolve." },
  { path: "/alerts", label: "Alerts", icon: Bell, phase: 8, blurb: "Proactive monitoring alerts from the watchdog agent." },
];
