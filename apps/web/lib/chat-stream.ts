// Minimal SSE parser for POST /api/v1/chat. The endpoint emits the
// canonical event vocabulary documented in agent/sse.py:
//   clarify, recommendation, token, degraded, error, done.
//
// We tolerate split frames — the server can flush a partial event in
// one chunk and complete it in the next — by buffering text until a
// blank-line delimiter appears.

export type ChatEvent =
  | { event: "clarify"; data: { question: string } }
  | {
      event: "recommendation";
      data: {
        fragrance: { slug: string; name: string; brand_slug: string };
        reasoning: string;
        rank: number;
        match_reason: string[];
      };
    }
  | { event: "token"; data: { text: string } }
  | { event: "degraded"; data: { reason: string; fallback: string } }
  | { event: "error"; data: { code: string; message: string } }
  | { event: "done"; data: { finish_reason: string } };

export async function* parseSSE(
  stream: ReadableStream<Uint8Array>,
  signal?: AbortSignal,
): AsyncGenerator<ChatEvent, void, void> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      if (signal?.aborted) break;
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let delim = buffer.indexOf("\n\n");
      while (delim !== -1) {
        const frame = buffer.slice(0, delim);
        buffer = buffer.slice(delim + 2);
        const ev = parseFrame(frame);
        if (ev) yield ev;
        delim = buffer.indexOf("\n\n");
      }
    }
  } finally {
    reader.releaseLock();
  }
}

function parseFrame(frame: string): ChatEvent | null {
  let event = "message";
  let data = "";
  for (const raw of frame.split("\n")) {
    const line = raw.trimEnd();
    if (!line || line.startsWith(":")) continue;
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      data += (data ? "\n" : "") + line.slice(5).trim();
    }
  }
  if (!data) return null;
  try {
    const parsed = JSON.parse(data);
    return { event, data: parsed } as ChatEvent;
  } catch {
    return null;
  }
}
