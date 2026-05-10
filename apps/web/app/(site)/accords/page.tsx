// Phase 4b: accords grid (list view).
// ISR: revalidate=3600 / tag=accords:all (set by getAllAccords fetcher,
// inherited from P4a).
import { Container } from "@/components/site/Container";
import { AccordCard } from "@/components/taxonomy/AccordCard";
import { ACCORD_COPY } from "@/lib/accord-copy";
import { getAllAccords } from "@/lib/api/fetchers";

export const metadata = {
  title: "Accords — Fragwise",
  description:
    "Browse the canonical accord families: woody, fougère, oriental, gourmand, aquatic, chypre, and more.",
};

function firstSentence(text: string): string {
  const match = text.match(/^[^.!?]*[.!?]/);
  return match ? match[0].trim() : text;
}

export default async function AccordsPage() {
  // Build-time graceful degradation (mirrors home page).
  let accords: Awaited<ReturnType<typeof getAllAccords>> = [];
  try {
    accords = await getAllAccords();
  } catch (err) {
    console.warn("[accords] getAllAccords failed — rendering empty grid.", err);
  }
  return (
    <Container className="py-12 md:py-20">
      <h1 className="mb-10 font-display text-4xl">Accords</h1>
      <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
        {accords.map((a) => {
          const copy = ACCORD_COPY[a.slug];
          return (
            <AccordCard
              key={a.slug}
              slug={a.slug}
              name={a.name}
              blurb={copy ? firstSentence(copy.blurb) : undefined}
            />
          );
        })}
      </div>
    </Container>
  );
}
