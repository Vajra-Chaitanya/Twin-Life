import { motion } from "framer-motion";
import { useId } from "react";
import { AnimatedNumber } from "./AnimatedNumber";

type Props = {
  value: number;
  label: string;
  color?: string;
  size?: number;
  delay?: number;
};

/** Radial 0-100 gauge with a metallic stroke that sweeps in. */
export function ScoreRing({ value, label, color = "#D4AF37", size = 150, delay = 0 }: Props) {
  const id = useId();
  const stroke = 10;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const pct = Math.max(0, Math.min(100, value)) / 100;

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative" style={{ width: size, height: size }}>
        <div
          className="absolute inset-4 rounded-full blur-2xl"
          style={{ background: color, opacity: 0.18 }}
          aria-hidden
        />
        <svg width={size} height={size} className="-rotate-90 overflow-visible" aria-hidden>
          <defs>
            <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stopColor="#F5E6B8" />
              <stop offset="0.6" stopColor={color} />
              <stop offset="1" stopColor="#8C6A1F" />
            </linearGradient>
          </defs>
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="rgb(212 175 55 / 0.1)" strokeWidth={stroke} />
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={`url(#${id})`}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: circumference * (1 - pct) }}
            transition={{ duration: 1.4, delay, ease: [0.22, 1, 0.36, 1] }}
            style={{ filter: `drop-shadow(0 0 6px ${color})` }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <AnimatedNumber value={value} className="font-display text-4xl font-bold text-ivory" />
          <span className="text-[10px] tracking-[0.2em] text-taupe uppercase">/ 100</span>
        </div>
      </div>
      <span className="font-display text-sm font-medium text-champagne">{label}</span>
    </div>
  );
}
