import { Link } from "react-router-dom";

export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <Link to="/" className="group flex items-center gap-3" aria-label="TwinLife AI home">
      <svg viewBox="0 0 64 64" className="h-9 w-9 transition-transform duration-500 group-hover:rotate-180">
        <defs>
          <linearGradient id="logo-gold" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#F5E6B8" />
            <stop offset="0.5" stopColor="#D4AF37" />
            <stop offset="1" stopColor="#8C6A1F" />
          </linearGradient>
        </defs>
        <circle cx="24" cy="32" r="13" fill="none" stroke="url(#logo-gold)" strokeWidth="4" />
        <circle cx="40" cy="32" r="13" fill="none" stroke="url(#logo-gold)" strokeWidth="4" />
      </svg>
      {!compact && (
        <span className="font-display text-lg font-semibold tracking-wide">
          <span className="text-metal">TwinLife</span> <span className="text-taupe">AI</span>
        </span>
      )}
    </Link>
  );
}
