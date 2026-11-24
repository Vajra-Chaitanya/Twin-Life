import { AnimatePresence, motion } from "framer-motion";
import { Check, MessageSquarePlus, MessagesSquare, Pencil, Search, Trash2, X } from "lucide-react";
import { useMemo, useState } from "react";
import type { ChatThread } from "../../lib/types";

const DAY = 86_400_000;

/** ChatGPT-style buckets: Today, Yesterday, Previous 7 days, Previous 30 days, then month names. */
function groupLabel(iso: string, now: Date) {
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const t = new Date(iso).getTime();
  if (t >= startOfToday) return "Today";
  if (t >= startOfToday - DAY) return "Yesterday";
  if (t >= startOfToday - 7 * DAY) return "Previous 7 days";
  if (t >= startOfToday - 30 * DAY) return "Previous 30 days";
  const d = new Date(iso);
  return d.toLocaleString("en-IN", { month: "long", ...(d.getFullYear() !== now.getFullYear() ? { year: "numeric" } : {}) });
}

type Props = {
  threads: ChatThread[];
  activeId: string;
  disabled?: boolean;
  onSelect: (id: string) => void;
  onNew: () => void;
  onRename: (id: string, title: string) => void;
  onDelete: (id: string) => void;
};

function Row({ thread, active, disabled, onSelect, onRename, onDelete }: {
  thread: ChatThread; active: boolean; disabled?: boolean;
  onSelect: () => void; onRename: (title: string) => void; onDelete: () => void;
}) {
  const [mode, setMode] = useState<"view" | "rename" | "confirm">("view");
  const [draft, setDraft] = useState(thread.title);

  if (mode === "rename") {
    return (
      <form
        className="flex items-center gap-1 rounded-lg bg-gold/10 px-2 py-1"
        onSubmit={(e) => {
          e.preventDefault();
          if (draft.trim()) onRename(draft.trim());
          setMode("view");
        }}
      >
        <input
          autoFocus
          value={draft}
          maxLength={120}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === "Escape" && setMode("view")}
          aria-label="Conversation name"
          className="min-w-0 flex-1 bg-transparent text-xs text-ivory outline-none"
        />
        <button type="submit" aria-label="Save name" className="text-good"><Check className="h-3.5 w-3.5" /></button>
        <button type="button" aria-label="Cancel" onClick={() => setMode("view")} className="text-taupe"><X className="h-3.5 w-3.5" /></button>
      </form>
    );
  }
  if (mode === "confirm") {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-risk/40 bg-risk/10 px-2 py-1.5 text-xs">
        <span className="min-w-0 flex-1 truncate text-ivory">Delete chat?</span>
        <button type="button" onClick={onDelete} className="font-semibold text-risk">Delete</button>
        <button type="button" onClick={() => setMode("view")} className="text-taupe">Cancel</button>
      </div>
    );
  }
  return (
    <div className={`group flex items-center gap-1 rounded-lg transition-colors ${active ? "bg-gold/15" : "hover:bg-gold/5"}`}>
      <button
        type="button"
        disabled={disabled}
        onClick={onSelect}
        title={`${thread.title} · ${thread.messages} message${thread.messages === 1 ? "" : "s"}`}
        className={`min-w-0 flex-1 truncate px-2 py-1.5 text-left text-xs ${active ? "text-champagne" : "text-ivory/85"}`}
      >
        {thread.title}
      </button>
      <span className={`flex shrink-0 gap-0.5 pr-1 ${active ? "" : "opacity-0 group-hover:opacity-100 group-focus-within:opacity-100"}`}>
        <button type="button" aria-label={`Rename ${thread.title}`} onClick={() => { setDraft(thread.title); setMode("rename"); }}
          className="rounded p-1 text-taupe hover:text-champagne">
          <Pencil className="h-3 w-3" />
        </button>
        <button type="button" aria-label={`Delete ${thread.title}`} onClick={() => setMode("confirm")}
          className="rounded p-1 text-taupe hover:text-risk">
          <Trash2 className="h-3 w-3" />
        </button>
      </span>
    </div>
  );
}

export function ConversationList({ threads, activeId, disabled, onSelect, onNew, onRename, onDelete }: Props) {
  const [query, setQuery] = useState("");
  const groups = useMemo(() => {
    const now = new Date();
    const q = query.trim().toLowerCase();
    const out: { label: string; items: ChatThread[] }[] = [];
    for (const t of threads) {
      if (q && !t.title.toLowerCase().includes(q)) continue;
      const label = groupLabel(t.updated_at, now);
      const group = out.find((g) => g.label === label) ?? out[out.push({ label, items: [] }) - 1];
      group.items.push(t);
    }
    return out;
  }, [threads, query]);

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <button type="button" onClick={onNew} disabled={disabled} className="btn-gold justify-center px-3 py-2 text-xs disabled:opacity-50">
        <MessageSquarePlus className="h-4 w-4" /> New chat
      </button>
      <label className="flex items-center gap-2 rounded-lg border border-gold/15 bg-ink/60 px-2 py-1.5 text-xs focus-within:border-gold/50">
        <Search className="h-3.5 w-3.5 text-taupe" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search chats"
          aria-label="Search chats"
          className="min-w-0 flex-1 bg-transparent text-ivory outline-none placeholder:text-taupe/60"
        />
      </label>
      <nav aria-label="Conversations" className="-mr-1 flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto pr-1">
        {threads.length === 0 && (
          <p className="flex items-center gap-2 px-2 text-xs text-taupe">
            <MessagesSquare className="h-3.5 w-3.5" /> Your conversations will appear here.
          </p>
        )}
        {threads.length > 0 && groups.length === 0 && <p className="px-2 text-xs text-taupe">No chats match “{query}”.</p>}
        <AnimatePresence initial={false}>
          {groups.map((g) => (
            <motion.section key={g.label} layout initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <h3 className="px-2 pb-1 text-[10px] font-semibold tracking-widest text-taupe uppercase">{g.label}</h3>
              <div className="flex flex-col gap-0.5">
                {g.items.map((t) => (
                  <Row
                    key={t.thread_id}
                    thread={t}
                    active={t.thread_id === activeId}
                    disabled={disabled}
                    onSelect={() => onSelect(t.thread_id)}
                    onRename={(title) => onRename(t.thread_id, title)}
                    onDelete={() => onDelete(t.thread_id)}
                  />
                ))}
              </div>
            </motion.section>
          ))}
        </AnimatePresence>
      </nav>
    </div>
  );
}
