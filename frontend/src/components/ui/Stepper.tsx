import { motion } from "framer-motion";
import { Check, type LucideIcon } from "lucide-react";

export type Step = { label: string; icon: LucideIcon };

export function Stepper({ steps, current, onSelect }: { steps: Step[]; current: number; onSelect: (i: number) => void }) {
  return (
    <ol className="relative flex items-center justify-between">
      <div className="absolute top-5 right-5 left-5 h-px bg-gold/15" aria-hidden />
      <motion.div
        className="absolute top-5 left-5 h-px origin-left"
        style={{ right: 20, background: "linear-gradient(90deg, #8C6A1F, #D4AF37, #F5E6B8)" }}
        initial={false}
        animate={{ scaleX: current / (steps.length - 1) }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        aria-hidden
      />
      {steps.map(({ label, icon: Icon }, i) => {
        const done = i < current;
        const active = i === current;
        return (
          <li key={label} className="relative z-10 flex flex-col items-center gap-2">
            <button
              type="button"
              onClick={() => i < current && onSelect(i)}
              disabled={i > current}
              aria-current={active ? "step" : undefined}
              aria-label={`Step ${i + 1}: ${label}`}
              className={`flex h-10 w-10 items-center justify-center rounded-full border transition-all duration-300 ${
                active
                  ? "border-gold bg-gold/20 text-champagne shadow-[0_0_24px_rgb(212_175_55/0.5)]"
                  : done
                    ? "border-gold/60 bg-gold text-ink"
                    : "border-gold/20 bg-ink text-taupe"
              }`}
            >
              {done ? <Check className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
            </button>
            <span className={`text-xs font-medium ${active ? "text-champagne" : "text-taupe"}`}>{label}</span>
          </li>
        );
      })}
    </ol>
  );
}
