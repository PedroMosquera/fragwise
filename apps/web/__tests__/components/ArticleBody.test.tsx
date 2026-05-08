import { render } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ArticleBody, SANITIZE_SCHEMA } from "@/components/editorial/ArticleBody";

// Negative XSS tests — the SANITIZE_SCHEMA MUST drop:
//   - <script> tags
//   - <iframe> tags
//   - every on* event handler attribute
//   - the `style` attribute
// Positive tests — GFM constructs (tables, fenced code) MUST render,
// and external anchors MUST gain rel="noopener noreferrer" target="_blank".

describe("ArticleBody — sanitize schema", () => {
  it("strips <script>, <iframe>, on* handlers, and style attributes", () => {
    const malicious = [
      "Hello world.",
      "",
      "<script>alert(1)</script>",
      "",
      '<iframe src="https://evil.example.com"></iframe>',
      "",
      '<a href="https://example.com" onclick="alert(1)">link</a>',
      "",
      '<p style="color:red">styled paragraph</p>',
    ].join("\n");

    const { container } = render(<ArticleBody body={malicious} />);
    const html = container.innerHTML;
    expect(html).not.toContain("<script");
    expect(html).not.toContain("<iframe");
    expect(html).not.toContain(" onclick=");
    // The style attribute MUST be stripped wherever it appears.
    expect(html).not.toMatch(/\sstyle=/);
  });

  it("renders GFM tables and fenced code blocks", () => {
    const md = [
      "| Feature | Supported |",
      "| ------- | --------- |",
      "| Tables  | yes       |",
      "",
      "```js",
      "const x = 1;",
      "```",
    ].join("\n");
    const { container } = render(<ArticleBody body={md} />);
    expect(container.querySelector("table")).not.toBeNull();
    expect(container.querySelector("pre code")).not.toBeNull();
  });

  it("rewrites external anchors with rel and target", () => {
    const md = "See [example](https://example.com) for details.";
    const { container } = render(<ArticleBody body={md} />);
    const anchor = container.querySelector("a");
    expect(anchor).not.toBeNull();
    expect(anchor!.getAttribute("href")).toBe("https://example.com");
    expect(anchor!.getAttribute("rel")).toBe("noopener noreferrer");
    expect(anchor!.getAttribute("target")).toBe("_blank");
  });

  it("does not add target=_blank to internal anchors", () => {
    const md = "See [our notes](/notes) for context.";
    const { container } = render(<ArticleBody body={md} />);
    const anchor = container.querySelector("a");
    expect(anchor).not.toBeNull();
    expect(anchor!.getAttribute("href")).toBe("/notes");
    expect(anchor!.getAttribute("target")).toBeNull();
    expect(anchor!.getAttribute("rel")).toBeNull();
  });

  it("renders a fallback when body is null", () => {
    const { container } = render(<ArticleBody body={null} />);
    expect(container.textContent).toContain("No body content available.");
  });
});

describe("SANITIZE_SCHEMA", () => {
  it("excludes script/iframe/style/link/meta/object/embed from tagNames", () => {
    const tags = SANITIZE_SCHEMA.tagNames ?? [];
    for (const banned of [
      "script",
      "iframe",
      "object",
      "embed",
      "style",
      "link",
      "meta",
    ]) {
      expect(tags).not.toContain(banned);
    }
  });

  it("strips style and on* from the global * attribute allowlist", () => {
    const star = SANITIZE_SCHEMA.attributes?.["*"] ?? [];
    const flatten = (a: unknown) => (Array.isArray(a) ? String(a[0]) : String(a));
    const names = star.map(flatten);
    expect(names).not.toContain("style");
    for (const n of names) {
      expect(n.startsWith("on")).toBe(false);
    }
  });

  it("locks anchor href to http, https, mailto", () => {
    const protocols = SANITIZE_SCHEMA.protocols?.href ?? [];
    expect(protocols).toEqual(expect.arrayContaining(["http", "https", "mailto"]));
    expect(protocols).not.toContain("javascript");
  });
});
