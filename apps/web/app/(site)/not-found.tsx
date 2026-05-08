import Link from "next/link";
import { Container } from "@/components/site/Container";

export default function NotFound() {
  return (
    <Container className="py-24 text-center">
      <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
        404
      </p>
      <h1 className="mt-3 font-display text-5xl">
        Not in the catalogue — yet.
      </h1>
      <p className="mt-6 text-muted-foreground">
        Either the URL is off, or this fragrance hasn&rsquo;t been added.
      </p>
      <Link
        href="/fragrances"
        className="mt-8 inline-block font-mono text-xs uppercase tracking-wider text-accent underline"
      >
        Browse fragrances
      </Link>
    </Container>
  );
}
