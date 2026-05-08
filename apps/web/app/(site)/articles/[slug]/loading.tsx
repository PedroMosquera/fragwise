// Phase 4b: skeleton for /articles/[slug] detail.
import { Container } from "@/components/site/Container";
import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <Container className="py-12 md:py-20">
      <article className="mx-auto max-w-prose">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="mt-4 h-12 w-3/4" />
        <Skeleton className="mt-12 h-64 w-full" />
      </article>
    </Container>
  );
}
