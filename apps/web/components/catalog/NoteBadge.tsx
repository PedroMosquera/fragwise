// NoteBadge.tsx — non-clickable in 4a (note details ship in 4b).
import { Badge } from "@/components/ui/badge";
import type { components } from "@/lib/api/types";

export function NoteBadge({
  note,
}: {
  note: components["schemas"]["NoteSummary"];
}) {
  return (
    <Badge variant="outline" className="font-sans text-sm">
      {note.name}
    </Badge>
  );
}
