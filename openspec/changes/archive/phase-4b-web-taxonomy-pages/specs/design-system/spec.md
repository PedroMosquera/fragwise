# Delta for design-system

## ADDED Requirements

### Requirement: Article Markdown Rendering Stack

`apps/web/package.json` runtime `dependencies` MUST include `react-markdown` at `^9`, `remark-gfm` at `^4`, and `rehype-sanitize` at `^6`. The `<ArticleBody>` component MUST compose them in this order: parse the markdown source, apply GFM extensions via `remark-gfm`, then sanitize the resulting HAST via `rehype-sanitize`. The sanitize schema MUST drop `<script>`, `<iframe>`, and any `on*` event-handler attributes; it MUST allow common formatting (headings, paragraphs, emphasis), code blocks, tables, lists, and links.

#### Scenario: Required deps pinned at major versions

- GIVEN `apps/web/package.json`
- WHEN parsing it as JSON
- THEN `dependencies` contains `react-markdown` matching `^9`
- AND `dependencies` contains `remark-gfm` matching `^4`
- AND `dependencies` contains `rehype-sanitize` matching `^6`

#### Scenario: ArticleBody pipeline order

- GIVEN the `<ArticleBody>` component source
- WHEN inspecting its plugin configuration
- THEN `remark-gfm` is registered as a remark plugin
- AND `rehype-sanitize` is registered as a rehype plugin AFTER any rehype transformations
- AND the sanitize schema explicitly disallows `script`, `iframe`, and `on*` attributes

#### Scenario: Sanitize schema allows common formatting

- GIVEN markdown input containing a heading, a code fence, a table, a list, and a link
- WHEN `<ArticleBody>` renders the input
- THEN the output contains `<h1>`/`<h2>`, `<pre><code>`, `<table>`, `<ul>`/`<ol>`, and `<a>` elements
- AND the link element carries the `rel="noopener noreferrer"` and `target="_blank"` attributes
