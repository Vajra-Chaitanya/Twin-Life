import { useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { CornerDownLeft, Database, Home, Loader2, Presentation, RefreshCw, Search, Sparkles, UserRound, type LucideIcon } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { assess } from "../lib/api";
import { loadPersona, seedDemo } from "../lib/demo";
import { isFullMotion, setFullMotion } from "../lib/motion";
import { NAV_ITEMS } from "../lib/nav";
import { PERSONAS } from "../lib/personas";
import { tour } from "../lib/tour";
import { getCurrentUser } from "../lib/user";
import { toast } from "./Toaster";

type Command = { id: string; group: string; label: string; hint?: string; icon: LucideIcon; run: () => void | Promise<unknown> };

const listeners = new Set<() => void>();
export const openCommandPalette = () => listeners.forEach((l) => l());

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [index, setIndex] = useState(0);
  const [busy, setBusy] = useState<string | null>(null);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const show = () => setOpen(true);
    listeners.add(show);
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => {
      listeners.delete(show);
      window.removeEventListener("keydown", onKey);
    };
  }, []);

  useEffect(() => {
    if (open) {
      setQuery("");
      setIndex(0);
      setTimeout(() => input.current?.focus(), 30);
    }
  }, [open]);

  const commands = useMemo<Command[]>(
    () => [
      { id: "home", group: "Navigate", label: "Home", icon: Home, run: () => navigate("/") },
      ...NAV_ITEMS.map((n) => ({ id: n.path, group: "Navigate", label: n.label, hint: n.blurb, icon: n.icon, run: () => navigate(n.path) })),
      ...PERSONAS.map((p) => ({
        id: `persona-${p.key}`,
        group: "Twins",
        label: `Load ${p.name}`,
        hint: p.tagline,
        icon: UserRound,
        run: async () => {
          await loadPersona(p, queryClient);
          toast(`${p.name} loaded`, { body: "Calibrated and assessed with synthetic data.", tone: "success" });
          navigate("/dashboard");
        },
      })),
      {
        id: "reassess",
        group: "Actions",
        label: "Re-assess current twin",
        icon: RefreshCw,
        run: async () => {
          const userId = getCurrentUser();
          if (!userId) return toast("No twin selected", { tone: "warning" });
          const snap = await assess(userId);
          await queryClient.invalidateQueries();
          toast(`Snapshot #${snap.snapshot_id} saved`, { tone: "success" });
        },
      },
      {
        id: "seed",
        group: "Actions",
        label: "Prepare demo data",
        hint: "Calibrate all personas, finish on Rahul",
        icon: Database,
        run: async () => {
          await seedDemo(queryClient);
          toast("Demo data ready", { body: "All personas calibrated. Rahul is active.", tone: "success" });
          navigate("/dashboard");
        },
      },
      { id: "tour", group: "Actions", label: "Start guided demo tour", icon: Presentation, run: () => tour.start() },
      {
        id: "motion",
        group: "Actions",
        label: isFullMotion() ? "Motion: follow system setting" : "Motion: full animations",
        icon: Sparkles,
        run: () => setFullMotion(!isFullMotion()),
      },
    ],
    // Rebuild when opened so the motion label reflects the current state.
    [open, navigate, queryClient],
  );

  const filtered = commands.filter((c) => {
    const haystack = `${c.label} ${c.hint ?? ""} ${c.group}`.toLowerCase();
    return query.toLowerCase().split(/\s+/).every((word) => haystack.includes(word));
  });

  async function execute(c: Command) {
    setBusy(c.id);
    try {
      await c.run();
      setOpen(false);
    } catch (err) {
      toast("Command failed", { body: err instanceof Error ? err.message : String(err), tone: "warning" });
    } finally {
      setBusy(null);
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[70] flex items-start justify-center bg-ink/70 px-4 pt-[15vh] backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onMouseDown={(e) => e.target === e.currentTarget && setOpen(false)}
        >
          <motion.div
            role="dialog"
            aria-label="Command palette"
            initial={{ opacity: 0, y: -16, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -16, scale: 0.97 }}
            transition={{ type: "spring", stiffness: 420, damping: 32 }}
            className="glass w-full max-w-xl overflow-hidden border-gold/30 shadow-[0_30px_80px_-20px_rgb(212_175_55/0.35)]"
          >
            <div className="flex items-center gap-3 border-b border-gold/15 px-4">
              <Search className="h-4 w-4 text-gold" />
              <input
                ref={input}
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setIndex(0);
                }}
                onKeyDown={(e) => {
                  if (e.key === "ArrowDown") {
                    e.preventDefault();
                    setIndex((i) => Math.min(filtered.length - 1, i + 1));
                  } else if (e.key === "ArrowUp") {
                    e.preventDefault();
                    setIndex((i) => Math.max(0, i - 1));
                  } else if (e.key === "Enter" && filtered[index]) {
                    e.preventDefault();
                    void execute(filtered[index]);
                  } else if (e.key === "Escape") {
                    setOpen(false);
                  }
                }}
                placeholder="Search pages, twins and actions…"
                aria-label="Command search"
                className="flex-1 bg-transparent py-4 text-ivory outline-none placeholder:text-taupe/60"
              />
              <kbd className="rounded border border-gold/20 px-1.5 py-0.5 font-mono text-[10px] text-taupe">ESC</kbd>
            </div>
            <ul className="max-h-[50vh] overflow-y-auto p-2" role="listbox">
              {filtered.length === 0 && <li className="px-3 py-6 text-center text-sm text-taupe">No matching commands</li>}
              {filtered.map((c, i) => {
                const Icon = c.icon;
                const showGroup = i === 0 || filtered[i - 1].group !== c.group;
                return (
                  <li key={c.id}>
                    {showGroup && <p className="px-3 pt-3 pb-1 text-[10px] tracking-[0.2em] text-taupe uppercase">{c.group}</p>}
                    <button
                      type="button"
                      role="option"
                      aria-selected={i === index}
                      onMouseEnter={() => setIndex(i)}
                      onClick={() => void execute(c)}
                      disabled={busy !== null}
                      className={`relative flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm ${i === index ? "text-champagne" : "text-ivory/85"}`}
                    >
                      {i === index && <motion.span layoutId="cmd-active" className="absolute inset-0 rounded-xl border border-gold/30 bg-gold/10" />}
                      <Icon className="relative h-4 w-4 text-gold" />
                      <span className="relative flex-1">
                        {c.label}
                        {c.hint && <span className="block truncate text-[11px] text-taupe">{c.hint}</span>}
                      </span>
                      {busy === c.id ? (
                        <Loader2 className="relative h-4 w-4 animate-spin text-gold" />
                      ) : (
                        i === index && <CornerDownLeft className="relative h-3.5 w-3.5 text-taupe" />
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
