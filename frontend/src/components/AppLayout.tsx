import { AnimatePresence, motion } from "framer-motion";
import { Search } from "lucide-react";
import { NavLink, useLocation, useOutlet } from "react-router-dom";
import { NAV_ITEMS } from "../lib/nav";
import { ApiStatus } from "./ApiStatus";
import { openCommandPalette } from "./CommandPalette";
import { Logo } from "./Logo";
import { MotionToggle } from "./MotionToggle";
import { NotificationBell } from "./NotificationBell";

export function AppLayout() {
  const location = useLocation();
  const outlet = useOutlet();
  const current = NAV_ITEMS.find((item) => location.pathname.startsWith(item.path));

  return (
    <div className="flex min-h-screen">
      <aside className="glass sticky top-4 m-4 hidden h-[calc(100vh-2rem)] w-64 shrink-0 flex-col p-5 md:flex">
        <Logo />
        <nav className="mt-10 flex flex-1 flex-col gap-1" aria-label="Main">
          {NAV_ITEMS.map(({ path, label, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              className={({ isActive }) =>
                `relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors ${
                  isActive ? "text-champagne" : "text-taupe hover:text-ivory"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.span
                      layoutId="nav-active"
                      className="absolute inset-0 rounded-xl border border-gold/30 bg-gold/10"
                      transition={{ type: "spring", stiffness: 420, damping: 34 }}
                    />
                  )}
                  <Icon className="relative h-4 w-4" />
                  <span className="relative">{label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>
        <p className="text-[11px] leading-relaxed text-taupe/70">
          Academic prototype. Not medical, financial or insurance advice.
        </p>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex flex-wrap items-center justify-between gap-4 px-4 pt-6 md:px-6">
          <div className="md:hidden">
            <Logo compact />
          </div>
          <h1 className="font-display text-xl font-semibold text-ivory md:text-2xl">
            {current?.label ?? "TwinLife AI"}
          </h1>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={openCommandPalette}
              className="glass hidden items-center gap-2 rounded-full px-3 py-1.5 text-xs whitespace-nowrap text-taupe hover:text-champagne sm:flex"
              aria-label="Open command palette"
            >
              <Search className="h-3.5 w-3.5" /> Search
              <kbd className="rounded border border-gold/20 px-1 font-mono text-[10px]">Ctrl K</kbd>
            </button>
            <MotionToggle />
            <ApiStatus />
            <NotificationBell />
          </div>
        </header>

        <nav className="flex gap-1 overflow-x-auto px-4 pt-4 md:hidden" aria-label="Main mobile">
          {NAV_ITEMS.map(({ path, icon: Icon, label }) => (
            <NavLink
              key={path}
              to={path}
              aria-label={label}
              className={({ isActive }) =>
                `rounded-lg p-2.5 ${isActive ? "bg-gold/15 text-champagne" : "text-taupe"}`
              }
            >
              <Icon className="h-5 w-5" />
            </NavLink>
          ))}
        </nav>

        <main className="flex-1 px-4 py-6 md:px-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 16, filter: "blur(6px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              exit={{ opacity: 0, y: -12, filter: "blur(6px)" }}
              transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            >
              {outlet}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}
