import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

type Props = {
  title: string;
  icon?: LucideIcon;
  accent?: string;
  subtitle?: ReactNode;
  action?: ReactNode;
  className?: string;
  children: ReactNode;
};

export const panelVariants = {
  hidden: { opacity: 0, y: 24, scale: 0.98 },
  show: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] as const } },
};

export function Panel({ title, icon: Icon, accent = "text-gold", subtitle, action, className = "", children }: Props) {
  return (
    <motion.section
      variants={panelVariants}
      whileHover={{ y: -3 }}
      transition={{ type: "spring", stiffness: 300, damping: 26 }}
      className={`glass group relative overflow-hidden p-6 transition-colors hover:border-gold/30 ${className}`}
    >
      <div
        className="pointer-events-none absolute -top-24 -right-24 h-48 w-48 rounded-full bg-gold/10 opacity-0 blur-3xl transition-opacity duration-500 group-hover:opacity-100"
        aria-hidden
      />
      <header className="relative mb-5 flex items-start justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 font-display text-sm font-semibold tracking-[0.18em] text-champagne uppercase">
            {Icon && <Icon className={`h-4 w-4 ${accent}`} />}
            {title}
          </h2>
          {subtitle && <p className="mt-1 text-xs text-taupe">{subtitle}</p>}
        </div>
        {action}
      </header>
      <div className="relative">{children}</div>
    </motion.section>
  );
}
