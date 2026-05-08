import { Skeleton } from "@/components/ui/skeleton";

export function FragranceCardSkeleton() {
  return (
    <div className="flex flex-col gap-3">
      <Skeleton className="aspect-[3/4] rounded-md" />
      <Skeleton className="h-3 w-16" />
      <Skeleton className="h-5 w-3/4" />
      <Skeleton className="h-3 w-1/3" />
    </div>
  );
}
