import { Fragment, type ReactNode } from "react";
import { FlaskConical } from "lucide-react";

// Minimal Markdown subset (paragraphs, bullets, numbered lists, headings, **bold**) rendered as React nodes, never raw HTML.
function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") && part.length > 4 ? (
      <strong key={i} className="font-semibold text-champagne">
        {part.slice(2, -2)}
      </strong>
    ) : (
      <Fragment key={i}>{part}</Fragment>
    ),
  );
}

type Block = { kind: "p" | "ul" | "ol" | "h"; lines: string[]; advice: boolean };

function toBlocks(text: string): Block[] {
  const blocks: Block[] = [];
  let inAdvice = false;
  // LLMs sometimes run list items together ("...zone.2. Next"); split them back, but never inside a decimal like "24.9)".
  const normalized = text.replace(/([^\d\s][.!?:])\s*(\d{1,2}[.)]\s+\S)/g, "$1\n$2");
  for (const raw of normalized.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line) {
      blocks.push({ kind: "p", lines: [], advice: inAdvice });
      continue;
    }
    const bullet = line.match(/^[-*•]\s+(.*)/);
    const numbered = line.match(/^\d+[.)]\s+(.*)/);
    const heading = line.match(/^#{1,4}\s+(.*)/);
    const kind = heading ? "h" : bullet ? "ul" : numbered ? "ol" : "p";
    const content = (heading ?? bullet ?? numbered)?.[1] ?? line;
    const section = content.replace(/\*\*/g, "").replace(/:$/, "").trim();
    if (/^(what you can do|what you should do|your plan|next steps|recommended actions|recommendations|actions)$/i.test(section)) inAdvice = true;
    else if ((heading || kind === "p") && /^(what changes|where you stand|why it matters|for you specifically|what happens|effect on your scores|expert assessment|try a simulation|disclaimer)$/i.test(section)) inAdvice = false;
    const last = blocks[blocks.length - 1];
    if (last && last.kind === kind && kind !== "h" && last.lines.length > 0 && last.advice === inAdvice) last.lines.push(content);
    else blocks.push({ kind, lines: [content], advice: inAdvice });
  }
  return blocks.filter((b) => b.lines.length > 0);
}

export const adviceKey = (line: string) => line.replace(/\*\*/g, "").replace(/\s+/g, " ").trim().toLowerCase();

export function Markdown({ text, onSimulate, canSimulate }: {
  text: string; onSimulate?: (advice: string) => void; canSimulate?: (line: string) => boolean;
}) {
  return (
    <div className="flex flex-col gap-3 text-[15px] leading-relaxed text-ivory/90">
      {toBlocks(text).map((block, i) => {
        if (block.kind === "h") {
          return (
            <h4 key={i} className="font-display font-semibold text-champagne">
              {inline(block.lines[0])}
            </h4>
          );
        }
        if (block.kind === "ul" || block.kind === "ol") {
          const List = block.kind === "ul" ? "ul" : "ol";
          return (
            <List key={i} className={`flex flex-col gap-1.5 pl-5 ${block.kind === "ul" ? "list-disc marker:text-gold" : "list-decimal marker:text-gold"}`}>
              {block.lines.map((line, j) => (
                <li key={j}>
                  {inline(line)}
                  {(block.kind === "ol" || block.advice) && onSimulate && (!canSimulate || canSimulate(line)) && (
                    <button type="button" className="ml-2 inline-flex items-center gap-1 text-xs text-champagne hover:underline"
                      onClick={(event) => { event.stopPropagation(); onSimulate(line); }}>
                      <FlaskConical className="h-3 w-3" /> Simulate
                    </button>
                  )}
                </li>
              ))}
            </List>
          );
        }
        return <p key={i}>{inline(block.lines.join(" "))}</p>;
      })}
    </div>
  );
}
