import { Container } from "@/components/site/Container";
import { FragranceCardSkeleton } from "@/components/catalog/FragranceCardSkeleton";

export default function Loading() {
  return (
    <Container className="py-16">
      <div className="grid grid-cols-2 gap-6 md:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <FragranceCardSkeleton key={i} />
        ))}
      </div>
    </Container>
  );
}
