import { animate, useInView } from "framer-motion";
import { useEffect, useRef, useState } from "react";

type Props = {
  value: number;
  format?: (n: number) => string;
  duration?: number;
  className?: string;
};

export function AnimatedNumber({ value, format = (n) => n.toFixed(0), duration = 1.1, className }: Props) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const [display, setDisplay] = useState(0);
  const previous = useRef(0);

  useEffect(() => {
    if (!inView || !Number.isFinite(value)) return;
    const controls = animate(previous.current, value, {
      duration,
      ease: [0.22, 1, 0.36, 1],
      onUpdate: (latest) => setDisplay(latest),
    });
    previous.current = value;
    return () => controls.stop();
  }, [value, inView, duration]);

  return (
    <span ref={ref} className={className}>
      {Number.isFinite(value) ? format(display) : "—"}
    </span>
  );
}
