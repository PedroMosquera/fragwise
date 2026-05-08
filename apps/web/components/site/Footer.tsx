// Open Question (per design.md): GitHub URL is a placeholder pending
// confirmation of the canonical org/repo. Update this single constant
// when the canonical URL is decided.
const REPO = "https://github.com/Iam2Fast/fragwise";

export function Footer() {
  return (
    <footer className="mt-24 border-t border-border bg-secondary/40">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-12 sm:px-6 md:flex-row md:items-center md:justify-between">
        <p className="font-display text-xl">Fragwise</p>
        <nav className="flex flex-wrap gap-6 font-mono text-xs uppercase tracking-wider text-muted-foreground">
          <a href={REPO} target="_blank" rel="noreferrer noopener">
            GitHub
          </a>
          <a
            href={`${REPO}/blob/main/LICENSE`}
            target="_blank"
            rel="noreferrer noopener"
          >
            License
          </a>
          <a
            href={`${REPO}/blob/main/CONTRIBUTING.md`}
            target="_blank"
            rel="noreferrer noopener"
          >
            Contributing
          </a>
        </nav>
        <p className="text-xs text-muted-foreground">
          © {new Date().getFullYear()} Fragwise — Apache-2.0
        </p>
      </div>
    </footer>
  );
}
