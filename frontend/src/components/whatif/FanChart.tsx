import { motion } from "framer-motion";
import { formatINR } from "../../lib/format";
import type { SavingsBand } from "../../lib/types";

const W = 640;
const H = 240;
const PAD = { top: 16, right: 16, bottom: 28, left: 64 };

const compact = new Intl.NumberFormat("en-IN", { notation: "compact", maximumFractionDigits: 1 });

/** Monte Carlo savings fan chart: p10–p90 band with median line, today vs simulated. */
export function FanChart({ before, after }: { before: SavingsBand[]; after: SavingsBand[] }) {
  const all = [...before, ...after];
  const lo = Math.min(0, ...all.map((p) => p.p10));
  const hi = Math.max(...all.map((p) => p.p90), 1);
  const months = Math.max(before.length, after.length);
  const x = (m: number) => PAD.left + ((m - 1) / Math.max(1, months - 1)) * (W - PAD.left - PAD.right);
  const y = (v: number) => PAD.top + (1 - (v - lo) / (hi - lo)) * (H - PAD.top - PAD.bottom);
  const band = (s: SavingsBand[]) =>
    `M ${s.map((p) => `${x(p.month)},${y(p.p90)}`).join(" L ")} L ${s
      .slice()
      .reverse()
      .map((p) => `${x(p.month)},${y(p.p10)}`)
      .join(" L ")} Z`;
  const median = (s: SavingsBand[]) => `M ${s.map((p) => `${x(p.month)},${y(p.median)}`).join(" L ")}`;
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => lo + t * (hi - lo));
  const last = after[after.length - 1];

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full overflow-visible" role="img" aria-label="Savings forecast fan chart">
        {ticks.map((v) => (
          <g key={v}>
            <line x1={PAD.left} x2={W - PAD.right} y1={y(v)} y2={y(v)} stroke="rgb(212 175 55 / 0.08)" />
            <text x={PAD.left - 8} y={y(v) + 4} textAnchor="end" className="fill-taupe text-[10px]">
              ₹{compact.format(v)}
            </text>
          </g>
        ))}
        {lo < 0 && <line x1={PAD.left} x2={W - PAD.right} y1={y(0)} y2={y(0)} stroke="#E5534B" strokeDasharray="3 4" opacity={0.6} />}
        {[1, Math.ceil(months / 2), months].map((m) => (
          <text key={m} x={x(m)} y={H - 8} textAnchor="middle" className="fill-taupe text-[10px]">
            M{m}
          </text>
        ))}

        <path d={band(before)} fill="rgb(201 206 214 / 0.10)" />
        <path d={median(before)} fill="none" stroke="#C9CED6" strokeWidth={1.5} strokeDasharray="5 5" opacity={0.7} />

        <motion.path
          d={band(after)}
          fill="rgb(212 175 55 / 0.22)"
          initial={false}
          animate={{ d: band(after) }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        />
        <motion.path
          d={median(after)}
          fill="none"
          stroke="#D4AF37"
          strokeWidth={2.5}
          style={{ filter: "drop-shadow(0 0 6px #D4AF37)" }}
          initial={false}
          animate={{ d: median(after) }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        />
        {last && <motion.circle r={5} fill="#F5E6B8" initial={false} animate={{ cx: x(last.month), cy: y(last.median) }} />}
      </svg>
      <div className="mt-2 flex flex-wrap justify-between gap-3 text-xs text-taupe">
        <span className="flex items-center gap-3">
          <span className="flex items-center gap-1.5">
            <span className="h-0.5 w-4 border-t border-dashed border-insurance" /> Today
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-1 w-4 rounded bg-gold" /> Simulated (band = 10th–90th percentile)
          </span>
        </span>
        {last && (
          <span>
            Median in {last.month} months: <span className="font-mono text-champagne">{formatINR(last.median)}</span>
          </span>
        )}
      </div>
    </div>
  );
}
