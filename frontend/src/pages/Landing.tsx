import { motion } from "framer-motion";
import { ArrowRight, HeartPulse, Presentation, ShieldCheck, Sparkles, Wallet } from "lucide-react";
import { Link } from "react-router-dom";
import { Logo } from "../components/Logo";
import { MotionToggle } from "../components/MotionToggle";
import { TwinVisual } from "../components/TwinVisual";
import { useLatestSnapshot } from "../lib/queries";
import { tour } from "../lib/tour";
import { useCurrentUser } from "../lib/user";

const DOMAINS = [
  { icon: HeartPulse, title: "Health Twin", color: "text-health", text: "CVD risk from a trained Random Forest, explained with SHAP, plus clinical formulas." },
  { icon: Wallet, title: "Finance Twin", color: "text-finance", text: "Stability, debt load and Monte Carlo forecasts of your savings runway." },
  { icon: ShieldCheck, title: "Insurance Twin", color: "text-insurance", text: "Coverage adequacy against health-driven future costs and rider gaps." },
];

const ORBITS = [
  { size: 260, duration: 18, color: "#E0A899" },
  { size: 340, duration: 26, color: "#D4AF37" },
  { size: 420, duration: 34, color: "#C9CED6" },
];

function TwinOrb() {
  return (
    <div className="relative flex h-[440px] w-[440px] items-center justify-center" aria-hidden>
      <div className="absolute h-40 w-40 rounded-full bg-gold/30 blur-3xl animate-pulse-glow" />
      <motion.div
        className="relative h-32 w-32 rounded-full"
        style={{
          background: "radial-gradient(circle at 35% 30%, #F5E6B8, #D4AF37 45%, #5c4512 100%)",
          boxShadow: "0 0 60px rgb(212 175 55 / 0.55), inset -10px -14px 30px rgb(0 0 0 / 0.45)",
        }}
        animate={{ scale: [1, 1.05, 1] }}
        transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
      />
      {ORBITS.map(({ size, duration, color }, i) => (
        <motion.div
          key={size}
          className="absolute rounded-full border"
          style={{ width: size, height: size, borderColor: `${color}33`, rotateX: 64, rotateZ: i * 30 }}
          animate={{ rotate: i % 2 ? -360 : 360 }}
          transition={{ duration, repeat: Infinity, ease: "linear" }}
        >
          <span
            className="absolute -top-1.5 left-1/2 h-3 w-3 -translate-x-1/2 rounded-full"
            style={{ background: color, boxShadow: `0 0 14px ${color}` }}
          />
        </motion.div>
      ))}
    </div>
  );
}

const container = { hidden: {}, show: { transition: { staggerChildren: 0.12, delayChildren: 0.15 } } };
const item = {
  hidden: { opacity: 0, y: 24, filter: "blur(8px)" },
  show: { opacity: 1, y: 0, filter: "blur(0px)", transition: { duration: 0.7, ease: [0.22, 1, 0.36, 1] as const } },
};

export function Landing() {
  const snapshot = useLatestSnapshot(useCurrentUser()).data;
  return (
    <div className="relative min-h-screen overflow-hidden">
      <div className="gold-grid absolute inset-0 -z-10" />
      <header className="mx-auto flex max-w-7xl items-center justify-between px-6 py-6">
        <Logo />
        <div className="flex items-center gap-3">
          <MotionToggle />
          <Link to="/dashboard" className="btn-ghost px-4 py-2 text-sm">
            Open console
          </Link>
        </div>
      </header>

      <section className="mx-auto grid max-w-7xl grid-cols-1 items-center gap-10 px-6 pt-6 pb-16 lg:grid-cols-2">
        <motion.div variants={container} initial="hidden" animate="show">
          <motion.span
            variants={item}
            className="inline-flex items-center gap-2 rounded-full border border-gold/25 bg-gold/5 px-3 py-1 text-xs tracking-widest text-champagne uppercase"
          >
            <Sparkles className="h-3.5 w-3.5" /> Agentic digital twin
          </motion.span>
          <motion.h1 variants={item} className="mt-6 font-display text-5xl leading-[1.05] font-bold md:text-7xl">
            Your life, <br />
            <span className="text-metal-animated">simulated.</span>
          </motion.h1>
          <motion.p variants={item} className="mt-6 max-w-lg text-lg text-taupe">
            One intelligent twin of your health, finances and insurance that explains your risks, forecasts your
            future and tests decisions before you make them.
          </motion.p>
          <motion.div variants={item} className="mt-10 flex flex-wrap gap-4">
            <Link to="/onboard" className="btn-gold">
              Calibrate my twin <ArrowRight className="h-4 w-4" />
            </Link>
            <Link to="/dashboard" className="btn-ghost">
              View dashboard
            </Link>
            <button type="button" onClick={tour.start} className="btn-ghost">
              <Presentation className="h-4 w-4" /> Guided tour
            </button>
          </motion.div>
        </motion.div>

        <motion.div
          className="flex min-w-0 flex-col items-center"
          initial={{ opacity: 0, scale: 0.85 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1.2, ease: [0.22, 1, 0.36, 1] }}
        >
          <TwinVisual risk={snapshot?.health.cardio_risk.probability} fallback={<TwinOrb />} />
          {snapshot && (
            <>
              <motion.h2
                className="-mt-6 mb-3 px-2 text-center font-display text-3xl font-bold tracking-wide sm:text-4xl md:text-5xl"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: [0, 1, 0.82, 1], y: 0 }}
                transition={{ duration: 1.4, delay: 0.6, times: [0, 0.5, 0.62, 1] }}
              >
                <span style={{ color: "#D4AF37", textShadow: "0 0 10px rgb(212 175 55 / 0.8), 0 0 26px rgb(212 175 55 / 0.5)" }}>Twin:</span>{" "}
                <span style={{ color: "#FFFFFF", textShadow: "0 0 10px rgb(255 255 255 / 0.55), 0 0 24px rgb(212 175 55 / 0.35)" }}>
                  {snapshot.user_id}
                </span>
              </motion.h2>
              <div className="flex flex-wrap justify-center gap-x-6 gap-y-2 sm:gap-x-8">
                {[
                  { label: "Health", value: snapshot.health.overall_health_score, color: "#E0A899" },
                  { label: "Financial", value: snapshot.finance.financial_stability_score, color: "#D4AF37" },
                  { label: "Insurance", value: snapshot.insurance.insurance_adequacy_score, color: "#C9CED6" },
                ].map((s, i) => (
                  <motion.div
                    key={s.label}
                    className="flex flex-col items-center"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.9 + i * 0.12 }}
                  >
                    <span className="font-display text-3xl font-bold" style={{ color: s.color, textShadow: `0 0 12px ${s.color}88` }}>
                      {s.value}
                    </span>
                    <span className="text-[10px] tracking-widest text-taupe uppercase">{s.label}</span>
                  </motion.div>
                ))}
              </div>
            </>
          )}
          <p className="mt-2 px-4 text-center text-[10px] text-taupe/50">
            3D head scan by Lee Perry-Smith (Infinite Realities), CC BY 3.0
          </p>
        </motion.div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-5 px-6 pb-20 md:grid-cols-3">
        {DOMAINS.map(({ icon: Icon, title, color, text }, i) => (
          <motion.article
            key={title}
            className="glass p-6"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.12, duration: 0.6 }}
            whileHover={{ y: -6, borderColor: "rgba(212,175,55,0.45)" }}
          >
            <Icon className={`h-7 w-7 ${color}`} />
            <h3 className="mt-4 font-display text-lg font-semibold">{title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-taupe">{text}</p>
          </motion.article>
        ))}
      </section>
    </div>
  );
}
