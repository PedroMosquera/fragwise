import { NoteBadge } from "./NoteBadge";
import type { components } from "@/lib/api/types";

type Notes = components["schemas"]["NotesByRole"];

const ROLES: { key: keyof Notes; label: string }[] = [
  { key: "top", label: "TOP" },
  { key: "heart", label: "HEART" },
  { key: "base", label: "BASE" },
];

export function Pyramid({ notes }: { notes: Notes }) {
  return (
    <div className="flex flex-col gap-6 border-l border-accent pl-6">
      {ROLES.map(({ key, label }) => {
        const list = notes[key] ?? [];
        return (
          <div key={key} className="flex flex-col gap-2">
            <span className="font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
              {label}
            </span>
            {list.length === 0 ? (
              <span
                aria-label={`No ${label.toLowerCase()} notes`}
                className="text-muted-foreground"
              >
                —
              </span>
            ) : (
              <div className="flex flex-wrap gap-2">
                {list.map((n) => (
                  <NoteBadge key={n.slug} note={n} />
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
