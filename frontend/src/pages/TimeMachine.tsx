import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, ChevronLeft, ChevronRight, Clock, History as HistoryIcon, Pause, Play, Sparkles, Wand2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { DeltaTable } from "../components/history/DeltaTable";
import { LifeEventsPanel } from "../components/history/LifeEventsPanel";
import { TrendChart } from "../components/history/TrendChart";
import { Panel } from "../components/dashboard/Panel";
import { ScoreRing } from "../components/ui/ScoreRing";
import { ApiError, assess, getHistory, onboard } from "../lib/api";
import { formatRelative } from "../lib/format";
import { buildJourney } from "../lib/journey";
import { PERSONAS } from "../lib/personas";
import { useLifeEvents } from "../lib/queries";
import { useCurrentUser } from "../lib/user";

const NOTES_KEY = "twinlife-snapshot-notes";
const readNotes = (): Record<string, string> => JSON.parse(localStorage.getItem(NOTES_KEY) ?? "{}");

const grid = { hidden: {}, show: { transition: { staggerChildren: 0.08 } } };

export function TimeMachine() {
  const userId = useCurrentUser();
  const queryClient = useQueryClient();
  const history = useQuery({
    queryKey: ["history", userId],
    enabled: Boolean(userId),
    queryFn: async () => {
      try {
        return (await getHistory(userId!, 100)).snapshots.slice().reverse();
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return [];
        throw err;
      }
    },
  });
  const snapshots = useMemo(() => history.data ?? [], [history.data]);

  const [selected, setSelected] = useState(0);
  const [compare, setCompare] = useState<"first" | "previous">("first");
  const [playing, setPlaying] = useState(false);
  const [journey, setJourney] = useState<{ done: number; total: number } | null>(null);
  const [journeyError, setJourneyError] = useState<string | null>(null);
  const [notes, setNotes] = useState(readNotes);
  const lifeEvents = useLifeEvents(userId);
  const eventNotes = useMemo(() => {
    const byId: Record<string, string> = {};
    for (const e of lifeEvents.data?.events ?? []) {
      if (e.undone || e.snapshot_id === null) continue;
      const label = `${e.domains.map((d) => d[0].toUpperCase() + d.slice(1)).join("+")}: ${e.summary}`;
      byId[e.snapshot_id] = byId[e.snapshot_id] ? `${byId[e.snapshot_id]}; ${label}` : label;
    }
    return byId;
  }, [lifeEvents.data]);

  useEffect(() => setSelected(Math.max(0, snapshots.length - 1)), [snapshots.length]);

  useEffect(() => {
    if (!playing) return;
    if (selected >= snapshots.length - 1) {
      setPlaying(false);
      return;
    }
    const timer = setTimeout(() => setSelected((s) => s + 1), 1300);
    return () => clearTimeout(timer);
  }, [playing, selected, snapshots.length]);

  const persona = PERSONAS.find((p) => p.payload.user_id === userId);

  async function generateJourney() {
    if (!persona) return;
    const steps = buildJourney(persona.payload);
    setJourney({ done: 0, total: steps.length });
    setJourneyError(null);
    const next = { ...readNotes() };
    try {
      for (const [k, step] of steps.entries()) {
        await onboard(step.payload);
        const snap = await assess(step.payload.user_id);
        next[snap.snapshot_id] = step.note;
        setJourney({ done: k + 1, total: steps.length });
        if (k === steps.length - 1) queryClient.setQueryData(["latest", userId], snap);
      }
      localStorage.setItem(NOTES_KEY, JSON.stringify(next));
      setNotes(next);
      await queryClient.invalidateQueries({ queryKey: ["history", userId] });
      void queryClient.invalidateQueries({ queryKey: ["notifications", userId] });
      void queryClient.invalidateQueries({ queryKey: ["inputs", userId] });
    } catch (err) {
      setJourneyError(err instanceof Error ? err.message : "Journey generation failed");
    } finally {
      setJourney(null);
    }
  }

  if (!userId) {
    return (
      <div className="glass mx-auto mt-10 max-w-xl p-10 text-center">
        <HistoryIcon className="mx-auto h-12 w-12 text-gold" />
        <h2 className="mt-5 font-display text-2xl font-semibold text-metal">No twin to rewind</h2>
        <Link to="/onboard" className="btn-gold mt-8">
          Calibrate twin
        </Link>
      </div>
    );
  }
  if (history.isPending) return <div className="glass h-96 animate-pulse" aria-busy />;
  if (history.isError) {
    return (
      <div className="glass mx-auto mt-10 max-w-lg p-8 text-center">
        <AlertTriangle className="mx-auto h-10 w-10 text-risk" />
        <p className="mt-4 text-taupe">Could not load history. Is the backend running?</p>
      </div>
    );
  }

  const current = snapshots[selected];
  const baseline = compare === "first" ? snapshots[0] : snapshots[Math.max(0, selected - 1)];

  const journeyButton = persona && (
    <button type="button" onClick={() => void generateJourney()} disabled={Boolean(journey)} className="btn-ghost px-3 py-1.5 text-xs disabled:opacity-60">
      <Wand2 className="h-3.5 w-3.5" />
      {journey ? `Simulating ${journey.done}/${journey.total}…` : "Generate demo journey"}
    </button>
  );

  if (!current) {
    return (
      <div className="glass mx-auto mt-10 max-w-xl p-10 text-center">
        <Clock className="mx-auto h-12 w-12 text-gold" />
        <h2 className="mt-5 font-display text-2xl font-semibold text-metal">No snapshots yet</h2>
        <p className="mt-2 text-taupe">Run an assessment to start the timeline.</p>
        <div className="mt-6 flex justify-center gap-3">{journeyButton}</div>
      </div>
    );
  }

  return (
    <motion.div variants={grid} initial="hidden" animate="show" className="grid gap-5 lg:grid-cols-3">
      {journeyError && (
        <p className="rounded-xl border border-risk/40 bg-risk/10 px-4 py-2 text-sm text-risk lg:col-span-3">{journeyError}</p>
      )}

      <Panel
        title="Twin trajectory"
        icon={HistoryIcon}
        subtitle={`${snapshots.length} snapshot${snapshots.length === 1 ? "" : "s"} for ${userId}`}
        className="lg:col-span-3"
        action={<div className="flex gap-2">{journeyButton}</div>}
      >
        {snapshots.length < 2 && (
          <p className="mb-4 flex items-center gap-2 text-sm text-taupe">
            <Sparkles className="h-4 w-4 text-gold" />
            Recalibrate with new inputs{persona ? " or generate a demo journey" : ""} to see your twin evolve.
          </p>
        )}
        <TrendChart snapshots={snapshots} selected={selected} onSelect={setSelected} />

        <div className="mt-6 flex items-center gap-3">
          <button type="button" aria-label="Previous snapshot" onClick={() => setSelected((s) => Math.max(0, s - 1))} className="btn-ghost p-2">
            <ChevronLeft className="h-4 w-4" />
          </button>
          <button
            type="button"
            aria-label={playing ? "Pause" : "Play timeline"}
            onClick={() => {
              if (!playing && selected >= snapshots.length - 1) setSelected(0);
              setPlaying((p) => !p);
            }}
            disabled={snapshots.length < 2}
            className="btn-gold p-3 disabled:opacity-50"
          >
            {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
          </button>
          <button
            type="button"
            aria-label="Next snapshot"
            onClick={() => setSelected((s) => Math.min(snapshots.length - 1, s + 1))}
            className="btn-ghost p-2"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
          <input
            type="range"
            aria-label="Timeline scrubber"
            min={0}
            max={Math.max(0, snapshots.length - 1)}
            value={selected}
            onChange={(e) => {
              setPlaying(false);
              setSelected(Number(e.target.value));
            }}
            className="gold-range flex-1"
            style={{ ["--pct" as string]: `${snapshots.length > 1 ? (selected / (snapshots.length - 1)) * 100 : 100}%` }}
          />
        </div>
      </Panel>

      <Panel
        title="Twin at this moment"
        icon={Clock}
        subtitle={
          <AnimatePresence mode="wait">
            <motion.span key={current.snapshot_id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              Snapshot #{current.snapshot_id} · {formatRelative(current.created_at)}
              {(notes[current.snapshot_id] ?? eventNotes[current.snapshot_id]) && (
                <span className="text-champagne"> · {notes[current.snapshot_id] ?? eventNotes[current.snapshot_id]}</span>
              )}
            </motion.span>
          </AnimatePresence>
        }
      >
        <div className="flex flex-col items-center gap-6">
          <ScoreRing value={current.health.overall_health_score} label="Health" color="#E0A899" size={130} />
          <div className="flex gap-6">
            <ScoreRing value={current.finance.financial_stability_score} label="Financial" color="#D4AF37" size={110} />
            <ScoreRing value={current.insurance.insurance_adequacy_score} label="Insurance" color="#C9CED6" size={110} />
          </div>
        </div>
      </Panel>

      <Panel
        title="What changed"
        icon={Sparkles}
        className="lg:col-span-2"
        action={
          <div role="radiogroup" aria-label="Compare against" className="flex rounded-lg border border-gold/15 p-0.5 text-xs">
            {(["first", "previous"] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                role="radio"
                aria-checked={compare === mode}
                onClick={() => setCompare(mode)}
                className={`rounded-md px-2.5 py-1 ${compare === mode ? "bg-gold/20 text-champagne" : "text-taupe"}`}
              >
                vs {mode}
              </button>
            ))}
          </div>
        }
      >
        <DeltaTable from={baseline} to={current} />
      </Panel>

      <LifeEventsPanel userId={userId} />
    </motion.div>
  );
}
