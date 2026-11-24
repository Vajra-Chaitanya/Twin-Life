import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, Info, X } from "lucide-react";
import { useSyncExternalStore } from "react";

type Tone = "info" | "warning" | "success";
type Toast = { id: number; title: string; body?: string; tone: Tone };

let toasts: Toast[] = [];
let nextId = 1;
const listeners = new Set<() => void>();
const emit = () => listeners.forEach((l) => l());

export function dismissToast(id: number) {
  toasts = toasts.filter((t) => t.id !== id);
  emit();
}

export function toast(title: string, options: { body?: string; tone?: Tone } = {}) {
  const id = nextId++;
  toasts = [...toasts.slice(-3), { id, title, body: options.body, tone: options.tone ?? "info" }];
  emit();
  setTimeout(() => dismissToast(id), 6000);
}

const ICON = { info: Info, warning: AlertTriangle, success: CheckCircle2 };
const COLOR = { info: "text-insurance", warning: "text-warn", success: "text-good" };

export function Toaster() {
  const items = useSyncExternalStore(
    (l) => {
      listeners.add(l);
      return () => listeners.delete(l);
    },
    () => toasts,
  );

  return (
    <div className="pointer-events-none fixed right-4 bottom-4 z-[60] flex w-80 flex-col gap-2" aria-live="polite">
      <AnimatePresence initial={false}>
        {items.map((t) => {
          const Icon = ICON[t.tone];
          return (
            <motion.div
              key={t.id}
              layout
              initial={{ opacity: 0, x: 60, scale: 0.95 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 60, scale: 0.95 }}
              transition={{ type: "spring", stiffness: 380, damping: 30 }}
              className="glass pointer-events-auto flex gap-3 border-gold/30 p-4"
              role="status"
            >
              <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${COLOR[t.tone]}`} />
              <div className="flex-1 text-sm">
                <p className="font-medium text-ivory">{t.title}</p>
                {t.body && <p className="mt-0.5 line-clamp-3 text-xs text-taupe">{t.body}</p>}
              </div>
              <button type="button" aria-label="Dismiss" onClick={() => dismissToast(t.id)} className="text-taupe hover:text-ivory">
                <X className="h-4 w-4" />
              </button>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
