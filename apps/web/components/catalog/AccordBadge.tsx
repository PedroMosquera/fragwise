import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import type { components } from "@/lib/api/types";

export function AccordBadge({
  accord,
}: {
  accord: components["schemas"]["AccordSummary"];
}) {
  return (
    <Link href={`/fragrances?accord=${accord.slug}`}>
      <Badge
        variant="secondary"
        className="font-mono text-[0.65rem] uppercase tracking-[0.16em]"
      >
        {accord.name}
      </Badge>
    </Link>
  );
}
