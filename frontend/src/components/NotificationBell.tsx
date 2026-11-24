import { AnimatePresence, motion } from "framer-motion";
import { Bell } from "lucide-react";
import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { useNotifications } from "../lib/notifications";
import { useCurrentUser } from "../lib/user";
import { toast } from "./Toaster";

export function NotificationBell() {
  const userId = useCurrentUser();
  const { data } = useNotifications(userId);
  const seenMax = useRef<number | null>(null);
  const unread = data?.unread ?? 0;

  useEffect(() => {
    seenMax.current = null;
  }, [userId]);

  useEffect(() => {
    if (!data) return;
    const maxId = Math.max(0, ...data.notifications.map((n) => n.id));
    if (seenMax.current !== null) {
      // Only toast alerts that arrived after the bell first loaded.
      data.notifications
        .filter((n) => n.id > seenMax.current! && n.type !== "baseline")
        .slice(0, 3)
        .forEach((n) => toast(n.severity === "warning" ? "Watchdog alert" : "Twin update", { body: n.message, tone: n.severity === "warning" ? "warning" : "info" }));
    }
    seenMax.current = maxId;
  }, [data]);

  return (
    <Link to="/alerts" aria-label={`Alerts, ${unread} unread`} className="glass relative flex h-8 w-8 items-center justify-center rounded-full text-taupe hover:text-champagne">
      <motion.span animate={unread > 0 ? { rotate: [0, -14, 12, -8, 0] } : {}} transition={{ duration: 0.8, repeat: unread > 0 ? Infinity : 0, repeatDelay: 4 }}>
        <Bell className="h-4 w-4" />
      </motion.span>
      <AnimatePresence>
        {unread > 0 && (
          <motion.span
            key={unread}
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            exit={{ scale: 0 }}
            className="absolute -top-1 -right-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-risk px-1 text-[10px] font-bold text-white"
          >
            {unread > 9 ? "9+" : unread}
          </motion.span>
        )}
      </AnimatePresence>
    </Link>
  );
}
