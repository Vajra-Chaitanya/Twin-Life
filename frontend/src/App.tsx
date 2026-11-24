import { lazy, Suspense, type ComponentType, type ReactNode } from "react";
import { Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/AppLayout";
import { CommandPalette } from "./components/CommandPalette";
import { DemoTour } from "./components/DemoTour";
import { GoldDust } from "./components/GoldDust";
import { Toaster } from "./components/Toaster";
import { NotFound } from "./pages/NotFound";

const named = <K extends string>(load: () => Promise<Record<K, ComponentType>>, key: K) =>
  lazy(() => load().then((m) => ({ default: m[key] })));

const Landing = named(() => import("./pages/Landing"), "Landing");
const Onboarding = named(() => import("./pages/Onboarding"), "Onboarding");
const Dashboard = named(() => import("./pages/Dashboard"), "Dashboard");
const TimeMachine = named(() => import("./pages/TimeMachine"), "TimeMachine");
const WhatIfLab = named(() => import("./pages/WhatIfLab"), "WhatIfLab");
const Advisor = named(() => import("./pages/Advisor"), "Advisor");
const Alerts = named(() => import("./pages/Alerts"), "Alerts");

function PageFallback() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center" aria-busy>
      <span className="h-10 w-10 animate-spin rounded-full border-2 border-gold/20 border-t-gold" />
    </div>
  );
}

const page = (node: ReactNode) => <Suspense fallback={<PageFallback />}>{node}</Suspense>;

export default function App() {
  return (
    <>
      <GoldDust />
      <Routes>
        <Route path="/" element={page(<Landing />)} />
        <Route element={<AppLayout />}>
          <Route path="/onboard" element={page(<Onboarding />)} />
          <Route path="/dashboard" element={page(<Dashboard />)} />
          <Route path="/history" element={page(<TimeMachine />)} />
          <Route path="/simulate" element={page(<WhatIfLab />)} />
          <Route path="/chat" element={page(<Advisor />)} />
          <Route path="/alerts" element={page(<Alerts />)} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
      <CommandPalette />
      <DemoTour />
      <Toaster />
    </>
  );
}
