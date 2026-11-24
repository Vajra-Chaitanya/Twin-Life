import { motion } from "framer-motion";
import type { Snapshot } from "../../lib/types";

const SERIES = [
  { key: "health", label: "Health", color: "#E0A899", get: (s: Snapshot) => s.health.overall_health_score },
  { key: "finance", label: "Financial", color: "#D4AF37", get: (s: Snapshot) => s.finance.financial_stability_score },
  { key: "insurance", label: "Insurance", color: "#C9CED6", get: (s: Snapshot) => s.insurance.insurance_adequacy_score },
];

const W = 720;
const H = 240;
const PAD = { top: 16, right: 24, bottom: 28, left: 36 };

type Props = { snapshots: Snapshot[]; selected: number; onSelect: (index: number) => void };

export function TrendChart({ snapshots, selected, onSelect }: Props) {
  const n = snapshots.length;
  const x = (i: number) => (n === 1 ? W / 2 : PAD.left + (i * (W - PAD.left - PAD.right)) / (n - 1));
  const y = (v: number) => PAD.top + (1 - v / 100) * (H - PAD.top - PAD.bottom);

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full overflow-visible" role="img" aria-label="Score trends over time">
        <defs>
          {SERIES.map((s) => (
            <linearGradient key={s.key} id={`area-${s.key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor={s.color} stopOpacity="0.22" />
              <stop offset="1" stopColor={s.color} stopOpacity="0" />
            </linearGradient>
          ))}
        </defs>

        {[0, 25, 50, 75, 100].map((v) => (
          <g key={v}>
            <line x1={PAD.left} x2={W - PAD.right} y1={y(v)} y2={y(v)} stroke="rgb(212 175 55 / 0.08)" />
            <text x={PAD.left - 8} y={y(v) + 4} textAnchor="end" className="fill-taupe text-[10px]">
              {v}
            </text>
          </g>
        ))}

        <motion.line
          x1={0}
          x2={0}
          y1={PAD.top}
          y2={H - PAD.bottom}
          stroke="#D4AF37"
          strokeDasharray="4 4"
          initial={false}
          animate={{ x: x(selected) }}
          transition={{ type: "spring", stiffness: 200, damping: 26 }}
        />

        {SERIES.map((s, si) => {
          const points = snapshots.map((snap, i) => `${x(i)},${y(s.get(snap))}`);
          const line = `M ${points.join(" L ")}`;
          const area = `${line} L ${x(n - 1)},${y(0)} L ${x(0)},${y(0)} Z`;
          return (
            <g key={s.key}>
              {n > 1 && (
                <motion.path
                  d={area}
                  fill={`url(#area-${s.key})`}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.6 + si * 0.15, duration: 0.8 }}
                />
              )}
              <motion.path
                d={line}
                fill="none"
                stroke={s.color}
                strokeWidth={2.5}
                strokeLinejoin="round"
                strokeLinecap="round"
                style={{ filter: `drop-shadow(0 0 6px ${s.color})` }}
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 1.4, delay: si * 0.15, ease: [0.22, 1, 0.36, 1] }}
              />
              {snapshots.map((snap, i) => (
                <motion.circle
                  key={snap.snapshot_id}
                  cx={x(i)}
                  cy={y(s.get(snap))}
                  fill={i === selected ? s.color : "#0B0A08"}
                  stroke={s.color}
                  strokeWidth={2}
                  initial={false}
                  animate={{ r: i === selected ? 6 : 3.5 }}
                />
              ))}
            </g>
          );
        })}

        {snapshots.map((snap, i) => (
          <rect
            key={snap.snapshot_id}
            x={x(i) - 14}
            y={PAD.top}
            width={28}
            height={H - PAD.top - PAD.bottom}
            fill="transparent"
            className="cursor-pointer"
            onClick={() => onSelect(i)}
          >
            <title>Snapshot #{snap.snapshot_id}</title>
          </rect>
        ))}
      </svg>
      <ul className="mt-2 flex justify-center gap-5 text-xs">
        {SERIES.map((s) => (
          <li key={s.key} className="flex items-center gap-1.5 text-taupe">
            <span className="h-2 w-4 rounded-full" style={{ background: s.color }} />
            {s.label}
          </li>
        ))}
      </ul>
    </div>
  );
}
