import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, BookOpen, Bot, History as HistoryIcon, Link2, MessageSquarePlus, Mic, MicOff, SendHorizonal, ShieldAlert, Sparkles, UserRound, Wrench, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { AgentTrace } from "../components/advisor/AgentTrace";
import { ConversationList } from "../components/advisor/ConversationList";
import { Markdown } from "../components/advisor/Markdown";
import { ScenarioCard } from "../components/advisor/ScenarioCard";
import { TwinUpdateCard } from "../components/advisor/TwinUpdateCard";
import { askAdvisor, deleteThread, getChatHistory, renameThread } from "../lib/api";
import { prefersReducedMotion } from "../lib/motion";
import { useLifeEvents, useRefreshTwin } from "../lib/queries";
import type { ChatMessage, LifeEvent, Twin } from "../lib/types";
import { useCurrentUser } from "../lib/user";

const SUGGESTIONS: Record<Twin | "main", string[]> = {
  main: [
    "What is driving my heart risk and how can I lower it?",
    "I bought a car for 8 lakh, my EMI is 15000 for 5 years",
    "Undo my last update",
    "Is my emergency fund enough?",
    "Can I afford a heart treatment costing 3 lakh rupees?",
    "Which insurance riders am I missing and why?",
  ],
  health: [
    "What is my diabetes risk and why?",
    "How can I lower my heart risk?",
    "I had fever for 3 days",
    "My HbA1c is 6.1",
    "What if I lose 5 kg?",
  ],
  finance: [
    "What do I owe right now?",
    "Is my emergency fund enough?",
    "I lent 50k to my friend",
    "Can I afford a 10000 EMI?",
    "I subscribed to Netflix for 649 a month",
  ],
  insurance: [
    "Which policies are due for renewal?",
    "I took bike insurance for 2500 a year",
    "How much life cover do I need?",
    "Which riders am I missing?",
    "Is my health cover enough?",
  ],
};

const NOTICE_KEY = "twinlife-ai-notice-dismissed";
const threadKey = (userId: string, domain?: Twin) => `twinlife-thread-${userId}${domain ? `-${domain}` : ""}`;
// "default" holds conversations saved before threads existed.
const readThread = (userId: string | null, domain?: Twin) =>
  (userId && localStorage.getItem(threadKey(userId, domain))) || (domain ? `${domain}-default` : "default");
const newThreadId = (domain?: Twin) => `${domain ?? "t"}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

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

type UndoProps = { undoneIds: Set<number>; onUndo: (event: LifeEvent) => void; undoing: boolean };

function AssistantMessage({
  message, animate, selected, onSelect, undo,
}: { message: ChatMessage; animate: boolean; selected: boolean; onSelect: () => void; undo: UndoProps }) {
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
        {Boolean(message.context_turns) && (
          <span className="flex items-center gap-1 rounded-full border border-gold/20 px-2 py-0.5 text-[10px] text-champagne">
            <Link2 className="h-3 w-3" /> Following up on {message.context_turns} earlier message{message.context_turns === 1 ? "" : "s"}
          </span>
        )}
        {message.routing.twins && <span className="ml-auto font-mono text-[10px] uppercase">{message.routing.twins.join(" · ")}</span>}
      </header>

      <TwinUpdateCard
        updates={message.updates ?? []}
        reverted={message.reverted ?? []}
        pending={message.pending_questions ?? []}
        {...undo}
      />
      {message.scenarios?.map((s) => <ScenarioCard key={s.headline} scenario={s} />)}

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

export function Advisor({ domain, embedded = false }: { domain?: Twin; embedded?: boolean } = {}) {
  const userId = useCurrentUser();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [freshId, setFreshId] = useState<number | null>(null);
  const [listening, setListening] = useState(false);
  const [noticeDismissed, setNoticeDismissed] = useState(() => embedded || localStorage.getItem(NOTICE_KEY) === "1");
  const [threadId, setThreadIdState] = useState(() => readThread(userId, domain));
  const [showHistory, setShowHistory] = useState(false);
  const recognition = useRef<SpeechRecognitionLike | null>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const Speech = getSpeechRecognition();
  const chatKey = ["chat", userId, domain ?? "main", threadId];

  useEffect(() => setThreadIdState(readThread(userId, domain)), [userId, domain]);
  const setThreadId = (id: string) => {
    if (userId) localStorage.setItem(threadKey(userId, domain), id);
    setThreadIdState(id);
    setSelectedId(null);
    setFreshId(null);
  };

  const history = useQuery({
    queryKey: chatKey,
    queryFn: () => getChatHistory(userId!, threadId, domain),
    enabled: Boolean(userId),
  });
  const refreshTwin = useRefreshTwin(userId);
  const lifeEvents = useLifeEvents(userId);
  const ask = useMutation({
    mutationFn: (q: string) => askAdvisor(userId!, q, threadId, domain),
    onSuccess: (message) => {
      queryClient.setQueryData<Awaited<ReturnType<typeof getChatHistory>>>(chatKey, (old) => ({
        user_id: userId!,
        threads: old?.threads ?? [],
        messages: [...(old?.messages ?? []), message],
      }));
      void queryClient.invalidateQueries({ queryKey: chatKey });
      if (message.updates?.length || message.reverted?.length) refreshTwin();
      setFreshId(message.chat_id);
      setSelectedId(message.chat_id);
    },
  });

  const messages = history.data?.messages ?? [];
  const threads = history.data?.threads ?? [];
  const listKey = ["chat", userId, domain ?? "main"];
  const rename = useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) => renameThread(userId!, id, title),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: listKey }),
  });
  const remove = useMutation({
    mutationFn: (id: string) => deleteThread(userId!, id),
    onSuccess: (_, id) => {
      if (id === threadId) setThreadId(threads.find((t) => t.thread_id !== id)?.thread_id ?? newThreadId(domain));
      void queryClient.invalidateQueries({ queryKey: listKey });
    },
  });

  // With no saved choice for this chat, reopen the most recent conversation instead of an empty one.
  useEffect(() => {
    if (!userId || localStorage.getItem(threadKey(userId, domain))) return;
    const latest = history.data?.threads[0]?.thread_id;
    if (latest && latest !== threadId) setThreadId(latest);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [history.data, userId, domain]);
  const selected = messages.find((m) => m.chat_id === selectedId) ?? messages[messages.length - 1] ?? null;

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: embedded ? "nearest" : "end" });
  }, [messages.length, ask.isPending, embedded]);

  const send = (text: string) => {
    const q = text.trim();
    if (q.length < 2 || ask.isPending) return;
    setDraft("");
    ask.mutate(q);
  };
  const undo: UndoProps = {
    undoneIds: new Set((lifeEvents.data?.events ?? []).filter((e) => e.undone).map((e) => e.id)),
    // Reverting is a conversation with the advisor, so it explains what changed back.
    onUndo: (event) => send(`Undo "${event.summary}" (#${event.id})`),
    undoing: ask.isPending,
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

  const conversations = {
    threads,
    activeId: threadId,
    disabled: ask.isPending,
    onSelect: (id: string) => {
      setThreadId(id);
      setShowHistory(false);
    },
    onNew: () => {
      setThreadId(newThreadId(domain));
      setShowHistory(false);
    },
    onRename: (id: string, title: string) => rename.mutate({ id, title }),
    onDelete: (id: string) => remove.mutate(id),
  };

  return (
    <div className={embedded ? "flex min-w-0 flex-col" : "grid gap-5 lg:grid-cols-[250px_minmax(0,1fr)] 2xl:grid-cols-[250px_minmax(0,1fr)_320px]"}>
      {!embedded && (
        <aside className="glass sticky top-4 hidden h-[calc(100vh-7rem)] flex-col p-3 lg:flex">
          <ConversationList {...conversations} />
        </aside>
      )}
      <div className={embedded ? "flex h-[72vh] min-h-[520px] min-w-0 flex-col gap-3" : "flex min-h-[calc(100vh-9rem)] min-w-0 flex-col gap-4"}>
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

        <div className={`glass flex items-center gap-2 p-2 ${embedded ? "" : "lg:hidden"}`}>
          <button
            type="button"
            onClick={() => setShowHistory((v) => !v)}
            aria-expanded={showHistory}
            className={`btn-ghost px-3 py-1.5 text-xs ${showHistory ? "border-gold/50 text-champagne" : ""}`}
          >
            <HistoryIcon className="h-3.5 w-3.5" /> {showHistory ? "Back to chat" : "Chats"}
            <span className="font-mono text-[10px] opacity-70">{threads.length}</span>
          </button>
          <span className="min-w-0 flex-1 truncate text-xs text-taupe">
            {threads.find((t) => t.thread_id === threadId)?.title ?? "New conversation"}
          </span>
          <button type="button" onClick={conversations.onNew} disabled={ask.isPending} aria-label="New chat"
            className="btn-ghost px-2 py-1.5 text-xs disabled:opacity-40">
            <MessageSquarePlus className="h-3.5 w-3.5" />
          </button>
        </div>

        {showHistory && (
          <div className={`glass min-h-0 flex-1 p-3 ${embedded ? "" : "lg:hidden"}`}>
            <ConversationList {...conversations} />
          </div>
        )}

        <div className={`flex flex-1 flex-col gap-4 ${embedded ? "min-h-0 overflow-y-auto pr-1" : ""} ${showHistory ? (embedded ? "hidden" : "hidden lg:flex") : ""}`}>
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
                <h2 className="font-display text-2xl font-semibold text-metal">
                  {domain ? `Ask your ${domain === "finance" ? "financial" : domain} twin` : "Ask your twin anything"}
                </h2>
                <p className="mt-1 text-sm text-taupe">
                  {domain
                    ? `This chat only answers ${domain} questions and records ${domain} updates.`
                    : "Answers combine your twin's data, medical & financial guidelines, and an autonomous agent."}
                </p>
              </div>
            </div>
          )}

          {messages.map((m) => (
            <div key={m.chat_id} className="flex flex-col gap-3">
              <motion.div initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} className="flex justify-end gap-2">
                <div className="flex max-w-[80%] flex-col items-end gap-1">
                  <p className="rounded-2xl rounded-tr-sm bg-gradient-to-br from-champagne via-gold to-bronze px-4 py-2.5 text-sm font-medium text-ink">
                    {m.query}
                  </p>
                  {m.refined_query && (
                    <p className="flex items-center gap-1 text-[11px] text-taupe" title="The advisor cleaned up typos before answering">
                      <Sparkles className="h-3 w-3 text-gold" /> Understood as: <span className="text-champagne">{m.refined_query}</span>
                    </p>
                  )}
                </div>
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-gold/30">
                  <UserRound className="h-4 w-4 text-gold" />
                </span>
              </motion.div>
              <AssistantMessage message={m} animate={m.chat_id === freshId} selected={selected?.chat_id === m.chat_id} onSelect={() => setSelectedId(m.chat_id)} undo={undo} />
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
                Understanding your message, then consulting your twins, guidelines and agent…
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

        <div className={`sticky bottom-0 z-10 flex min-w-0 flex-col gap-3 bg-gradient-to-t from-ink via-ink/95 to-transparent ${embedded ? "pt-2 pb-0" : "pt-8 pb-4"}`}>
          <div className="flex gap-2 overflow-x-auto pb-1 [scrollbar-width:none]">
            {SUGGESTIONS[domain ?? "main"].map((s) => (
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
              placeholder={domain ? `Ask about your ${domain}, or tell me what changed…` : "Ask a question, or tell me what changed (“I bought a car…”, “I had surgery…”)"}
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

      {!embedded && (
        <div className="hidden 2xl:block">
          <AgentTrace message={ask.isPending ? null : selected} pending={ask.isPending} />
        </div>
      )}
    </div>
  );
}
