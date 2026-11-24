import { motion } from "framer-motion";
import { useId, type ReactNode } from "react";

type NumberFieldProps = {
  label: string;
  value: number;
  onChange: (value: number) => void;
  unit?: string;
  min?: number;
  max?: number;
  step?: number;
  slider?: boolean;
  error?: string;
  hint?: ReactNode;
};

export function NumberField({ label, value, onChange, unit, min, max, step = 1, slider, error, hint }: NumberFieldProps) {
  const id = useId();
  const hasSlider = slider && min !== undefined && max !== undefined;
  const pct = hasSlider && Number.isFinite(value) ? ((Math.min(Math.max(value, min), max) - min) / (max - min)) * 100 : 0;

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-xs font-medium tracking-wide text-taupe uppercase">
        {label}
      </label>
      <div
        className={`flex items-center rounded-xl border bg-ink/60 px-3 transition-colors focus-within:border-gold/70 focus-within:shadow-[0_0_0_3px_rgb(212_175_55/0.12)] ${
          error ? "border-risk/60" : "border-gold/15"
        }`}
      >
        <input
          id={id}
          type="number"
          inputMode="decimal"
          value={Number.isFinite(value) ? value : ""}
          min={min}
          max={max}
          step={step}
          onChange={(e) => onChange(e.target.value === "" ? NaN : Number(e.target.value))}
          aria-invalid={Boolean(error)}
          className="w-full bg-transparent py-2.5 font-mono text-ivory outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none"
        />
        {unit && <span className="pl-2 text-xs whitespace-nowrap text-taupe">{unit}</span>}
      </div>
      {hasSlider && (
        <input
          type="range"
          aria-label={`${label} slider`}
          min={min}
          max={max}
          step={step}
          value={Number.isFinite(value) ? value : min}
          onChange={(e) => onChange(Number(e.target.value))}
          className="gold-range"
          style={{ ["--pct" as string]: `${pct}%` }}
        />
      )}
      {error ? <span className="text-xs text-risk">{error}</span> : hint && <span className="text-xs text-taupe/80">{hint}</span>}
    </div>
  );
}

type Option<T> = { value: T; label: string };

export function Segmented<T extends string | number>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: Option<T>[];
  onChange: (value: T) => void;
}) {
  const group = useId();
  return (
    <div className="flex flex-col gap-2">
      <span className="text-xs font-medium tracking-wide text-taupe uppercase">{label}</span>
      <div role="radiogroup" aria-label={label} className="flex rounded-xl border border-gold/15 bg-ink/60 p-1">
        {options.map((option) => {
          const active = option.value === value;
          return (
            <button
              key={String(option.value)}
              type="button"
              role="radio"
              aria-checked={active}
              onClick={() => onChange(option.value)}
              className={`relative flex-1 rounded-lg px-3 py-1.5 text-sm transition-colors ${
                active ? "text-ink" : "text-taupe hover:text-ivory"
              }`}
            >
              {active && (
                <motion.span
                  layoutId={`seg-${group}`}
                  className="absolute inset-0 rounded-lg"
                  style={{ background: "linear-gradient(135deg, #F5E6B8, #D4AF37 60%, #A8862A)" }}
                  transition={{ type: "spring", stiffness: 500, damping: 36 }}
                />
              )}
              <span className="relative font-medium">{option.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
