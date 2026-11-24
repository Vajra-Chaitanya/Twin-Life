import { useQuery } from "@tanstack/react-query";
import { getHealth } from "../lib/api";

export function ApiStatus() {
  const { isSuccess, isPending } = useQuery({
    queryKey: ["api-health"],
    queryFn: getHealth,
    refetchInterval: 10_000,
    retry: false,
  });

  const label = isPending ? "Connecting…" : isSuccess ? "Twin engine online" : "Engine offline";
  const color = isPending ? "bg-warn" : isSuccess ? "bg-good" : "bg-risk";

  return (
    <div
      role="status"
      className="glass flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium whitespace-nowrap text-taupe"
    >
      <span className="relative flex h-2 w-2">
        {isSuccess && <span className={`absolute inline-flex h-full w-full animate-ping rounded-full ${color} opacity-60`} />}
        <span className={`relative inline-flex h-2 w-2 rounded-full ${color}`} />
      </span>
      {label}
    </div>
  );
}
