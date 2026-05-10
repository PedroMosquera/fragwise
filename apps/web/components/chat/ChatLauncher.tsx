// ChatLauncher — header button + slide-over Sheet that hosts the
// conversation with Wisp. Wisp is the project's editorial-perfumery
// chat persona; the panel POSTs to the existing /api/v1/chat SSE
// endpoint and renders the canonical event vocabulary inline:
//   clarify, token, recommendation, degraded, error, done.
//
// State model: the conversation is a flat list of turns. Each
// assistant turn is an array of `parts` so we can interleave streaming
// text, recommendation cards, and degraded-mode callouts in render
// order, which is how the spec says they're meant to be read.
"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import {
  Sheet,
  SheetContent,
  SheetTrigger,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { WispAvatar } from "@/components/chat/WispAvatar";
import { parseSSE, type ChatEvent } from "@/lib/chat-stream";

type Recommendation = Extract<ChatEvent, { event: "recommendation" }>["data"];
type Degraded = Extract<ChatEvent, { event: "degraded" }>["data"];

type AssistantPart =
  | { kind: "text"; text: string }
  | { kind: "clarify"; question: string }
  | { kind: "recommendation"; data: Recommendation }
  | { kind: "degraded"; data: Degraded }
  | { kind: "error"; message: string };

type Turn =
  | { role: "user"; content: string }
  | { role: "assistant"; parts: AssistantPart[]; finished: boolean };

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function ChatLauncher() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [streaming, setStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll the conversation as new tokens land.
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [turns]);

  // Cancel any in-flight request when the panel closes mid-stream.
  useEffect(() => {
    if (!open && abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
  }, [open]);

  async function send(message: string) {
    const trimmed = message.trim();
    if (!trimmed || streaming) return;

    const history = turns.flatMap<{ role: "user" | "assistant"; content: string }>(
      (t) => {
        if (t.role === "user") return [{ role: "user", content: t.content }];
        const txt = t.parts
          .map((p) => {
            if (p.kind === "text") return p.text;
            if (p.kind === "clarify") return p.question;
            if (p.kind === "recommendation") return p.data.reasoning;
            return "";
          })
          .join(" ")
          .trim();
        return txt ? [{ role: "assistant", content: txt }] : [];
      },
    );
    const body = {
      messages: [...history, { role: "user", content: trimmed }],
    };

    const userTurn: Turn = { role: "user", content: trimmed };
    const assistantTurn: Turn = {
      role: "assistant",
      parts: [],
      finished: false,
    };
    setTurns((prev) => [...prev, userTurn, assistantTurn]);
    setInput("");
    setStreaming(true);

    const ctrl = new AbortController();
    abortRef.current = ctrl;
    try {
      const resp = await fetch(`${API_URL}/api/v1/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: ctrl.signal,
      });
      if (!resp.ok || !resp.body) {
        throw new Error(`Chat request failed (${resp.status})`);
      }
      for await (const ev of parseSSE(resp.body, ctrl.signal)) {
        appendPart(ev);
      }
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      const message = err instanceof Error ? err.message : "Unknown error";
      setTurns((prev) =>
        appendToLastAssistant(prev, { kind: "error", message }),
      );
    } finally {
      setStreaming(false);
      abortRef.current = null;
      setTurns((prev) => markLastAssistantFinished(prev));
    }
  }

  function appendPart(ev: ChatEvent) {
    setTurns((prev) => {
      switch (ev.event) {
        case "token":
          return appendOrExtendText(prev, ev.data.text);
        case "clarify":
          return appendToLastAssistant(prev, {
            kind: "clarify",
            question: ev.data.question,
          });
        case "recommendation":
          return appendToLastAssistant(prev, {
            kind: "recommendation",
            data: ev.data,
          });
        case "degraded":
          return appendToLastAssistant(prev, { kind: "degraded", data: ev.data });
        case "error":
          return appendToLastAssistant(prev, {
            kind: "error",
            message: ev.data.message,
          });
        case "done":
          return prev;
      }
    });
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-md border border-border bg-card px-3 py-1.5 text-sm font-medium text-foreground shadow-sm transition-colors hover:bg-accent hover:text-accent-foreground"
        >
          <WispAvatar size={20} ariaLabel="" />
          <span>Chat with Wisp</span>
        </button>
      </SheetTrigger>
      <SheetContent
        side="right"
        className="flex h-full w-full flex-col gap-0 sm:max-w-md"
      >
        <SheetHeader className="border-b border-border">
          <div className="flex items-center gap-3">
            <span className="text-accent">
              <WispAvatar
                size={36}
                state={streaming ? "thinking" : "idle"}
              />
            </span>
            <div>
              <SheetTitle className="font-display text-xl">Wisp</SheetTitle>
              <SheetDescription>
                Your editorial guide to fragrance.
              </SheetDescription>
            </div>
          </div>
        </SheetHeader>

        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto px-4 py-6"
          aria-live="polite"
          aria-busy={streaming}
        >
          {turns.length === 0 ? (
            <WispWelcome onPick={(p) => void send(p)} />
          ) : (
            <ol className="flex flex-col gap-6">
              {turns.map((t, i) => (
                <li key={i}>
                  {t.role === "user" ? (
                    <UserBubble content={t.content} />
                  ) : (
                    <AssistantBubble parts={t.parts} streaming={!t.finished} />
                  )}
                </li>
              ))}
            </ol>
          )}
        </div>

        <form
          className="border-t border-border p-4"
          onSubmit={(e) => {
            e.preventDefault();
            void send(input);
          }}
        >
          <label className="sr-only" htmlFor="wisp-input">
            Ask Wisp
          </label>
          <div className="flex gap-2">
            <input
              id="wisp-input"
              type="text"
              autoComplete="off"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Smoky leather for winter…"
              disabled={streaming}
              className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
            <button
              type="submit"
              disabled={streaming || !input.trim()}
              className="rounded-md bg-primary px-4 py-2 font-mono text-xs uppercase tracking-wider text-primary-foreground disabled:opacity-50"
            >
              Send
            </button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
}

function appendToLastAssistant(turns: Turn[], part: AssistantPart): Turn[] {
  const idx = lastAssistantIdx(turns);
  if (idx === -1) return turns;
  const t = turns[idx];
  if (t.role !== "assistant") return turns;
  const next: Turn = { ...t, parts: [...t.parts, part] };
  return turns.map((x, i) => (i === idx ? next : x));
}

function appendOrExtendText(turns: Turn[], text: string): Turn[] {
  const idx = lastAssistantIdx(turns);
  if (idx === -1) return turns;
  const t = turns[idx];
  if (t.role !== "assistant") return turns;
  const last = t.parts[t.parts.length - 1];
  let parts: AssistantPart[];
  if (last && last.kind === "text") {
    parts = [...t.parts.slice(0, -1), { kind: "text", text: last.text + text }];
  } else {
    parts = [...t.parts, { kind: "text", text }];
  }
  return turns.map((x, i) => (i === idx ? { ...t, parts } : x));
}

function markLastAssistantFinished(turns: Turn[]): Turn[] {
  const idx = lastAssistantIdx(turns);
  if (idx === -1) return turns;
  const t = turns[idx];
  if (t.role !== "assistant") return turns;
  return turns.map((x, i) => (i === idx ? { ...t, finished: true } : x));
}

function lastAssistantIdx(turns: Turn[]): number {
  for (let i = turns.length - 1; i >= 0; i -= 1) {
    if (turns[i].role === "assistant") return i;
  }
  return -1;
}

function UserBubble({ content }: { content: string }) {
  return (
    <div className="flex justify-end">
      <p className="max-w-[85%] rounded-lg bg-secondary px-3 py-2 text-sm">
        {content}
      </p>
    </div>
  );
}

function AssistantBubble({
  parts,
  streaming,
}: {
  parts: AssistantPart[];
  streaming: boolean;
}) {
  return (
    <div className="flex gap-3">
      <span className="mt-1 text-accent">
        <WispAvatar size={24} state={streaming ? "thinking" : "idle"} />
      </span>
      <div className="flex flex-1 flex-col gap-3">
        {parts.length === 0 && streaming ? (
          <p className="text-sm text-muted-foreground">Wisp is thinking…</p>
        ) : null}
        {parts.map((p, i) => (
          <PartView key={i} part={p} />
        ))}
      </div>
    </div>
  );
}

function PartView({ part }: { part: AssistantPart }) {
  switch (part.kind) {
    case "text":
      return (
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
          {part.text}
        </p>
      );
    case "clarify":
      return (
        <p className="text-sm leading-relaxed text-foreground">
          {part.question}
        </p>
      );
    case "recommendation":
      return <RecommendationCard data={part.data} />;
    case "degraded":
      return (
        <p className="rounded-md border border-dashed border-border bg-muted/40 px-3 py-2 font-mono text-[0.7rem] uppercase tracking-wider text-muted-foreground">
          Wisp is in {part.data.reason.replaceAll("_", " ")} mode — fallback:{" "}
          {part.data.fallback.replaceAll("_", " ")}.
        </p>
      );
    case "error":
      return (
        <p className="rounded-md border border-destructive bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {part.message}
        </p>
      );
  }
}

function RecommendationCard({ data }: { data: Recommendation }) {
  return (
    <Link
      href={`/fragrances/${data.fragrance.slug}`}
      className="block rounded-md border border-border bg-card p-3 transition-colors hover:bg-accent hover:text-accent-foreground"
    >
      <p className="font-mono text-[0.6rem] uppercase tracking-[0.22em] text-muted-foreground">
        Pick #{data.rank} · {data.fragrance.brand_slug.replaceAll("-", " ")}
      </p>
      <p className="mt-1 font-display text-base">{data.fragrance.name}</p>
      {data.reasoning ? (
        <p className="mt-2 text-sm leading-snug text-foreground/85">
          {data.reasoning}
        </p>
      ) : null}
      {data.match_reason.length > 0 ? (
        <ul className="mt-2 flex flex-wrap gap-1.5">
          {data.match_reason.map((tag) => (
            <li
              key={tag}
              className="rounded-sm bg-secondary px-1.5 py-0.5 font-mono text-[0.6rem] uppercase tracking-wider text-secondary-foreground"
            >
              {tag}
            </li>
          ))}
        </ul>
      ) : null}
    </Link>
  );
}

function WispWelcome({ onPick }: { onPick: (q: string) => void }) {
  const examples = [
    "smoky leather for winter",
    "something woody but quiet for the office",
    "a cool aquatic for hot afternoons",
  ];
  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm leading-relaxed text-foreground">
        I read fragrance notes, accords, and the journal. Tell me what
        you&apos;re after — a mood, a scene, a season — and I&apos;ll pull a
        few from the catalogue.
      </p>
      <div className="flex flex-col gap-2">
        <p className="font-mono text-[0.7rem] uppercase tracking-wider text-muted-foreground">
          Try
        </p>
        {examples.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => onPick(q)}
            className="rounded-md border border-border bg-card px-3 py-2 text-left text-sm transition-colors hover:bg-accent hover:text-accent-foreground"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
