import { useQuery } from "@tanstack/react-query";
import { MessagesSquare, ScanLine } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Panel } from "../dashboard/Panel";
import { ApiError, getInputs } from "../../lib/api";
import { useLatestSnapshot } from "../../lib/queries";
import type { OnboardPayload, Snapshot, Twin } from "../../lib/types";
import { useCurrentUser } from "../../lib/user";
import { Advisor } from "../../pages/Advisor";
import { TWINS } from "../history/LifeEventsPanel";

export function useTwinInputs(userId: string | null) {
  return useQuery({
    queryKey: ["inputs", userId],
    enabled: Boolean(userId),
    queryFn: async (): Promise<OnboardPayload | null> => {
      try {
        return await getInputs(userId!);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      }
    },
  });
}

type Content = (ctx: { userId: string; snapshot: Snapshot; inputs: OnboardPayload | null }) => ReactNode;

/** Shared layout: the twin's own content on the left, its domain-only chat on the right. */
export function TwinPage({ domain, intro, children }: { domain: Twin; intro: string; children: Content }) {
  const userId = useCurrentUser();
  const latest = useLatestSnapshot(userId);
  const inputs = useTwinInputs(userId);
  const twin = TWINS[domain];
  const Icon = twin.icon;

  if (!userId || latest.data === null) {
    return (
      <div className="glass mx-auto mt-10 max-w-xl p-10 text-center">
        <ScanLine className="mx-auto h-12 w-12 text-gold" />
        <h2 className="mt-5 font-display text-2xl font-semibold text-metal">Calibrate a twin first</h2>
        <Link to="/onboard" className="btn-gold mt-8">Calibrate twin</Link>
      </div>
    );
  }
  if (latest.isPending || !latest.data) return <div className="glass h-96 animate-pulse" aria-busy />;

  return (
    <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_440px]">
      <div className="flex min-w-0 flex-col gap-5">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-2xl border" style={{ borderColor: `${twin.color}55`, background: `${twin.color}14` }}>
            <Icon className="h-5 w-5" style={{ color: twin.color }} />
          </span>
          <p className="text-sm text-taupe">{intro}</p>
        </div>
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">{children({ userId, snapshot: latest.data, inputs: inputs.data ?? null })}</div>
      </div>
      <div className="min-w-0 xl:sticky xl:top-4 xl:self-start">
        <Panel title={`${domain === "finance" ? "Financial" : twin.label} chat`} icon={MessagesSquare} subtitle={`Answers only ${domain} questions`}>
          <Advisor domain={domain} embedded />
        </Panel>
      </div>
    </div>
  );
}
