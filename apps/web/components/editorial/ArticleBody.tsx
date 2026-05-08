// Phase 4b: ArticleBody — sanitized markdown renderer. ADRs 0041–0043.
//
// Pipeline order (per ADR-0041):
//   parse → remark-gfm (remark plugin) → HAST conversion →
//   rehype-sanitize (rehype plugin, last)
//
// SANITIZE_SCHEMA (ADR-0042) starts from rehype-sanitize's
// `defaultSchema` and:
//   - drops these tags: script, iframe, object, embed, style, link, meta
//   - drops the `style` attribute and every `on*` event handler
//   - allows headings, paragraphs, emphasis, code/pre, lists, tables,
//     anchors (href, title, rel, target), code className for language
//     hints
//   - restricts href protocols to http, https, mailto
//
// Anchor rewriting (ADR-0043) happens via the `components` prop, which
// runs AFTER sanitize so it never reintroduces removed attributes.
// External links (http/https) gain `rel="noopener noreferrer"` and
// `target="_blank"`. Internal anchors are left untouched.
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize, {
  defaultSchema,
  type Options as Schema,
} from "rehype-sanitize";

const TAGS_TO_DROP = new Set([
  "script",
  "iframe",
  "object",
  "embed",
  "style",
  "link",
  "meta",
]);

function attrName(attr: unknown): string {
  return Array.isArray(attr) ? String(attr[0]) : String(attr);
}

export const SANITIZE_SCHEMA: Schema = {
  ...defaultSchema,
  // Filter out unsafe top-level tag names from the default allowlist.
  tagNames: (defaultSchema.tagNames ?? []).filter(
    (t) => !TAGS_TO_DROP.has(t),
  ),
  attributes: {
    ...defaultSchema.attributes,
    // Strip the catch-all `style` attribute and every `on*` event
    // handler from the global "*" allowlist. Belt-and-suspenders: the
    // default schema does not list `on*` handlers, but we filter
    // defensively in case a future default ever adds one.
    "*": (defaultSchema.attributes?.["*"] ?? []).filter((attr) => {
      const name = attrName(attr);
      return name !== "style" && !name.startsWith("on");
    }),
    // Anchor: allow href/title plus rel/target so the components-prop
    // override (ExternalAnchor) can inject them without sanitize
    // stripping them back out.
    a: ["href", "title", "rel", "target"],
    // code: allow `className` so language-hint classes (e.g.
    // "language-tsx") survive sanitize for downstream syntax
    // highlighters.
    code: ["className"],
  },
  protocols: {
    ...defaultSchema.protocols,
    href: ["http", "https", "mailto"],
  },
};

function ExternalAnchor({
  href,
  children,
  ...rest
}: React.AnchorHTMLAttributes<HTMLAnchorElement>) {
  const isExternal =
    typeof href === "string" && /^https?:\/\//i.test(href);
  return (
    <a
      href={href}
      {...(isExternal && { rel: "noopener noreferrer", target: "_blank" })}
      {...rest}
    >
      {children}
    </a>
  );
}

export function ArticleBody({ body }: { body: string | null }) {
  if (!body) {
    return (
      <p className="text-muted-foreground">No body content available.</p>
    );
  }
  return (
    <div className="prose prose-stone max-w-prose">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeSanitize, SANITIZE_SCHEMA]]}
        components={{ a: ExternalAnchor }}
      >
        {body}
      </ReactMarkdown>
    </div>
  );
}
