import { motion } from "framer-motion";
import { AnimatedNumber } from "../ui/AnimatedNumber";

const LABEL_COLOR: Record<string, string> = {
  Low: "#7FB77E",
  Moderate: "#E9B949",
  Elevated: "#E9A649",
  High: "#E5534B",
  "Very High": "#E5534B",
};

/** Semicircular gauge for a 0-1 probability. */
export function RiskGauge({ probability, label }: { probability: number; label: string }) {
  const width = 240;
  const r = 100;
  const cx = width / 2;
  const cy = 115;
  const arc = `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`;
  const angle = -90 + Math.max(0, Math.min(1, probability)) * 180;
  const color = LABEL_COLOR[label] ?? "#D4AF37";

  return (
    <div className="flex flex-col items-center">
      <svg viewBox={`0 0 ${width} 135`} className="w-full max-w-[260px]" aria-hidden>
        <defs>
          <linearGradient id="risk-arc" x1="0" x2="1">
            <stop offset="0" stopColor="#7FB77E" />
            <stop offset="0.5" stopColor="#E9B949" />
            <stop offset="1" stopColor="#E5534B" />
          </linearGradient>
        </defs>
        <path d={arc} fill="none" stroke="rgb(212 175 55 / 0.1)" strokeWidth="14" strokeLinecap="round" />
        <motion.path
          d={arc}
          fill="none"
          stroke="url(#risk-arc)"
          strokeWidth="14"
          strokeLinecap="round"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: probability }}
          transition={{ duration: 1.4, ease: [0.22, 1, 0.36, 1] }}
        />
        <motion.g
          style={{ originX: `${cx}px`, originY: `${cy}px` }}
          initial={{ rotate: -90 }}
          animate={{ rotate: angle }}
          transition={{ type: "spring", stiffness: 60, damping: 12, delay: 0.2 }}
        >
          <line x1={cx} y1={cy} x2={cx} y2={cy - r + 22} stroke="#F5E6B8" strokeWidth="3" strokeLinecap="round" />
        </motion.g>
        <circle cx={cx} cy={cy} r="7" fill="#D4AF37" />
      </svg>
      <div className="-mt-2 text-center">
        <AnimatedNumber
          value={probability * 100}
          format={(n) => `${n.toFixed(1)}%`}
          className="font-display text-4xl font-bold text-ivory"
        />
        <p className="mt-1 text-sm font-semibold tracking-widest uppercase" style={{ color }}>
          {label} risk
        </p>
      </div>
    </div>
  );
}
