import { Sparkles } from "lucide-react";
import { setFullMotion, useFullMotion } from "../lib/motion";

export function MotionToggle() {
  const full = useFullMotion();
  return (
    <button
      type="button"
      onClick={() => setFullMotion(!full)}
      aria-pressed={full}
      title={full ? "Full motion on (overrides system setting)" : "Motion follows system setting"}
      className={`glass flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors ${
        full ? "text-champagne" : "text-taupe hover:text-ivory"
      }`}
    >
      <Sparkles className={`h-3.5 w-3.5 ${full ? "text-gold" : ""}`} />
      {full ? "Motion: full" : "Motion: system"}
    </button>
  );
}
