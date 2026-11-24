import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, BookOpen, Bot, Mic, MicOff, SendHorizonal, ShieldAlert, Sparkles, UserRound, Wrench, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { AgentTrace } from "../components/advisor/AgentTrace";
import { Markdown } from "../components/advisor/Markdown";
import { askAdvisor, getChatHistory } from "../lib/api";
import { prefersReducedMotion } from "../lib/motion";
import type { ChatMessage } from "../lib/types";
import { useCurrentUser } from "../lib/user";

const SUGGESTIONS = [
  "What is driving my heart risk and how can I lower it?",
  "Is my emergency fund enough?",
  "Can I afford a heart treatment costing 3 lakh rupees?",
  "Which insurance riders am I missing and why?",
];

const NOTICE_KEY = "twinlife-ai-notice-dismissed";

type SpeechRecognitionLike = {
  lang: string;
  interimResults: boolean;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

function getSpeechRecognition(): (new () => SpeechRecognitionLike) | null {
  const w = window as unknown as Record<string, unknown>;
  return (w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null) as (new () => SpeechRecognitionLike) | null;
}

function useTypewriter(text: string, enabled: boolean) {
  const words = text.split(/(\s+)/);
  const [count, setCount] = useState(enabled ? 0 : words.length);
  useEffect(() => {
    if (!enabled || prefersReducedMotion()) {
      setCount(words.length);
      return;
    }
    setCount(0);
    const timer = setInterval(() => {
      setCount((c) => {
        if (c >= words.length) {
          clearInterval(timer);
          return c;
        }
        return c + 3;
      });
    }, 30);
    return () => clearInterval(timer);
  }, [text, enabled, words.length]);
  return { shown: words.slice(0, count).join(""), done: count >= words.length };
}

function AssistantMessage({ message, animate, selected, onSelect }: { message: ChatMessage; animate: boolean; selected: boolean; onSelect: () => void }) {
  const { shown, done } = useTypewriter(message.narration, animate);
  const sim = message.simulation;

  return (
    <motion.article
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      onClick={onSelect}
      className={`glass cursor-pointer p-5 transition-colors ${selected ? "border-gold/40" : "hover:border-gold/25"}`}
    >
      <header className="mb-3 flex items-center gap-2 text-xs text-taupe">
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-gold/15">
          <Bot className="h-3.5 w-3.5 text-gold" />
        </span>
        TwinLife Advisor
        {message.routing.twins && <span className="ml-auto font-mono text-[10px] uppercase">{message.routing.twins.join(" · ")}</span>}
      </header>

      {message.narration_error ? (
        <p className="flex items-center gap-2 text-sm text-warn">
          <AlertTriangle className="h-4 w-4" /> {message.narration_error}
        </p>
      ) : (
        <>
          <Markdown text={shown} />
          {!done && <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-gold align-middle" />}
        </>
      )}

      {done && sim && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-5 rounded-xl border border-gold/20 bg-gold/5 p-4">
          <p className="mb-2 flex items-center gap-2 text-xs font-semibold tracking-widest text-champagne uppercase">
            <Wrench className="h-3.5 w-3.5 text-gold" /> Treatment agent recommendation
          </p>
          {"error" in sim ? <p className="text-sm text-warn">{sim.error}</p> : <Markdown text={sim.recommendation} />}
        </motion.div>
      )}

      {done && message.citations.length > 0 && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-5">
          <p className="mb-2 flex items-center gap-2 text-[10px] tracking-widest text-taupe uppercase">
            <BookOpen className="h-3 w-3" /> Grounded in
          </p>
          <div className="grid gap-2 md:grid-cols-3">
            {message.citations.map((c, i) => (
              <details key={i} className="group rounded-xl border border-gold/10 bg-ink/50 p-3 text-xs" onClick={(e) => e.stopPropagation()}>
                <summary className="flex cursor-pointer list-none items-center justify-between gap-2">
                  <span className="truncate text-ivory/90">{c.source.replace(/_/g, " ").replace(".txt", "")}</span>
                  <span className="shrink-0 font-mono text-gold">{c.score === null ? "" : `${Math.round(c.score * 100)}%`}</span>
                </summary>
                <p className="mt-2 leading-relaxed text-taupe">{c.excerpt}…</p>
              </details>
            ))}
          </div>
        </motion.div>
      )}
    </motion.article>
  );
}

export function Advisor() {
  const userId = useCurrentUser();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [freshId, setFreshId] = useState<number | null>(null);
  const [listening, setListening] = useState(false);
  const [noticeDismissed, setNoticeDismissed] = useState(() => localStorage.getItem(NOTICE_KEY) === "1");
  const recognition = useRef<SpeechRecognitionLike | null>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const Speech = getSpeechRecognition();

  const history = useQuery({
    queryKey: ["chat", userId],
    queryFn: async () => (await getChatHistory(userId!)).messages,
    enabled: Boolean(userId),
  });
  const ask = useMutation({
    mutationFn: (q: string) => askAdvisor(userId!, q),
    onSuccess: (message) => {
      queryClient.setQueryData<ChatMessage[]>(["chat", userId], (old) => [...(old ?? []), message]);
      setFreshId(message.chat_id);
      setSelectedId(message.chat_id);
    },
  });

  const messages = history.data ?? [];
  const selected = messages.find((m) => m.chat_id === selectedId) ?? messages[messages.length - 1] ?? null;

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, ask.isPending]);

  const send = (text: string) => {
    const q = text.trim();
    if (q.length < 2 || ask.isPending) return;
    setDraft("");
    ask.mutate(q);
  };

  const toggleVoice = () => {
    if (!Speech) return;
    if (listening) {
      recognition.current?.stop();
      return;
    }
    const r = new Speech();
    r.lang = "en-IN";
    r.interimResults = true;
    r.onresult = (e) => setDraft(Array.from(e.results).map((res) => res[0].transcript).join(""));
    r.onend = () => setListening(false);
    recognition.current = r;
    setListening(true);
    r.start();
  };

  if (!userId) {
    return (
      <div className="glass mx-auto mt-10 max-w-xl p-10 text-center">
        <Bot className="mx-auto h-12 w-12 text-gold" />
        <h2 className="mt-5 font-display text-2xl font-semibold text-metal">Calibrate a twin to talk to the advisor</h2>
        <Link to="/onboard" className="btn-gold mt-8">Calibrate twin</Link>
      </div>
    );
  }

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
      <div className="flex min-h-[calc(100vh-9rem)] min-w-0 flex-col gap-4">
        <AnimatePresence>
          {!noticeDismissed && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="flex items-start gap-3 rounded-xl border border-warn/30 bg-warn/5 px-4 py-3 text-xs text-taupe"
            >
              <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-warn" />
              <p className="flex-1">
                Questions and this twin's profile are sent to Google Gemini to generate answers. Use synthetic demo data only.
                Answers are illustrative, not medical, financial or insurance advice.
              </p>
              <button
                type="button"
                aria-label="Dismiss notice"
                onClick={() => {
                  localStorage.setItem(NOTICE_KEY, "1");
                  setNoticeDismissed(true);
                }}
              >
                <X className="h-4 w-4" />
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="flex flex-1 flex-col gap-4">
          {history.isPending && <div className="glass h-40 animate-pulse" />}
          {messages.length === 0 && !history.isPending && !ask.isPending && (
            <div className="flex flex-1 flex-col items-center justify-center gap-6 py-10 text-center">
              <motion.div
                className="flex h-20 w-20 items-center justify-center rounded-full"
                style={{ background: "radial-gradient(circle at 35% 30%, #F5E6B8, #D4AF37 45%, #5c4512 100%)", boxShadow: "0 0 50px rgb(212 175 55 / 0.5)" }}
                animate={{ scale: [1, 1.06, 1] }}
                transition={{ duration: 2.4, repeat: Infinity }}
              >
                <Sparkles className="h-8 w-8 text-ink" />
              </motion.div>
              <div>
                <h2 className="font-display text-2xl font-semibold text-metal">Ask your twin anything</h2>
                <p className="mt-1 text-sm text-taupe">Answers combine your twin's data, medical & financial guidelines, and an autonomous agent.</p>
              </div>
            </div>
          )}

          {messages.map((m) => (
            <div key={m.chat_id} className="flex flex-col gap-3">
              <motion.div initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} className="flex justify-end gap-2">
                <p className="max-w-[80%] rounded-2xl rounded-tr-sm bg-gradient-to-br from-champagne via-gold to-bronze px-4 py-2.5 text-sm font-medium text-ink">
                  {m.query}
                </p>
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-gold/30">
                  <UserRound className="h-4 w-4 text-gold" />
                </span>
              </motion.div>
              <AssistantMessage message={m} animate={m.chat_id === freshId} selected={selected?.chat_id === m.chat_id} onSelect={() => setSelectedId(m.chat_id)} />
            </div>
          ))}

          {ask.isPending && (
            <div className="flex flex-col gap-3">
              <div className="flex justify-end">
                <p className="max-w-[80%] rounded-2xl rounded-tr-sm bg-gold/20 px-4 py-2.5 text-sm text-champagne">{ask.variables}</p>
              </div>
              <div className="glass flex items-center gap-3 p-5 text-sm text-taupe">
                <span className="flex gap-1">
                  {[0, 1, 2].map((i) => (
                    <motion.span
                      key={i}
                      className="h-2 w-2 rounded-full bg-gold"
                      animate={{ y: [0, -6, 0], opacity: [0.4, 1, 0.4] }}
                      transition={{ duration: 0.9, repeat: Infinity, delay: i * 0.15 }}
                    />
                  ))}
                </span>
                Consulting your twins, guidelines and agent…
              </div>
            </div>
          )}
          {ask.isError && (
            <p className="flex items-center gap-2 rounded-xl border border-risk/40 bg-risk/10 px-4 py-2 text-sm text-risk">
              <AlertTriangle className="h-4 w-4" /> {ask.error.message}
            </p>
          )}
          <div ref={bottom} />
        </div>

        <div className="sticky bottom-0 z-10 flex min-w-0 flex-col gap-3 bg-gradient-to-t from-ink via-ink/95 to-transparent pt-8 pb-4">
          <div className="flex gap-2 overflow-x-auto pb-1 [scrollbar-width:none]">
            {SUGGESTIONS.map((s) => (
              <motion.button
                key={s}
                type="button"
                whileHover={{ y: -2 }}
                whileTap={{ scale: 0.97 }}
                disabled={ask.isPending}
                onClick={() => send(s)}
                className="shrink-0 rounded-full border border-gold/20 bg-ink/80 px-3 py-1.5 text-xs whitespace-nowrap text-taupe backdrop-blur transition-colors hover:border-gold/60 hover:text-champagne disabled:opacity-50"
              >
                {s}
              </motion.button>
            ))}
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(draft);
            }}
            className="glass flex items-end gap-2 p-2 focus-within:border-gold/50"
          >
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send(draft);
                }
              }}
              rows={1}
              maxLength={1000}
              placeholder="Ask about your health, money or cover…"
              aria-label="Your question"
              className="max-h-40 flex-1 resize-none bg-transparent px-3 py-2.5 text-sm text-ivory outline-none placeholder:text-taupe/60"
            />
            {Speech && (
              <button
                type="button"
                onClick={toggleVoice}
                aria-pressed={listening}
                aria-label={listening ? "Stop voice input" : "Voice input"}
                title="Voice input uses your browser's speech service"
                className={`relative rounded-xl p-2.5 transition-colors ${listening ? "bg-risk/20 text-risk" : "text-taupe hover:text-champagne"}`}
              >
                {listening && <span className="absolute inset-0 animate-ping rounded-xl bg-risk/20" />}
                {listening ? <MicOff className="relative h-5 w-5" /> : <Mic className="relative h-5 w-5" />}
              </button>
            )}
            <button type="submit" disabled={ask.isPending || draft.trim().length < 2} className="btn-gold p-2.5 disabled:opacity-50" aria-label="Send">
              <SendHorizonal className="h-5 w-5" />
            </button>
          </form>
        </div>
      </div>

      <AgentTrace message={ask.isPending ? null : selected} pending={ask.isPending} />
    </div>
  );
}
