// Phase 4b: notes tree (list view).
// ISR: revalidate=3600 / tag=notes:tree (set by getAllNotes fetcher).
import { Container } from "@/components/site/Container";
import { NoteTree } from "@/components/taxonomy/NoteTree";
import { getAllNotes } from "@/lib/api/fetchers";

export const metadata = {
  title: "Notes — Fragwise",
  description:
    "The full perfumery taxonomy of olfactive notes — from citrus to oud, browsable as a tree.",
};

export default async function NotesPage() {
  // Build-time graceful degradation (mirrors home page): if the API is
  // unreachable at `next build` (CI/transient), render the empty tree
  // shell instead of failing the build. ISR refills once API is up.
  let tree: Awaited<ReturnType<typeof getAllNotes>> = [];
  try {
    tree = await getAllNotes();
  } catch (err) {
    console.warn("[notes] getAllNotes failed — rendering empty tree.", err);
  }
  return (
    <Container className="py-12 md:py-20">
      <h1 className="mb-10 font-display text-4xl">Notes</h1>
      <NoteTree nodes={tree} />
    </Container>
  );
}
