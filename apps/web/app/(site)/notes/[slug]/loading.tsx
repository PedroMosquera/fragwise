// Phase 4b: skeleton for /notes/[slug] detail.
import { Container } from "@/components/site/Container";
import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <Container className="py-12 md:py-20">
      <Skeleton className="h-4 w-24" />
      <Skeleton className="mt-4 h-12 w-3/4" />
      <Skeleton className="mt-8 h-32 w-full" />
    </Container>
  );
}
