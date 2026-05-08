// Phase 4b ADR-0048: debounced URL ?q= search input.
//
// 300 ms debounce via setTimeout. Updates wrap in `startTransition` so
// the input remains responsive while the RSC refetches. Resets the
// `?offset=` param whenever `q` changes (otherwise typing on page 3
// would keep the user on a now-meaningless offset).
//
// `paramKey` defaults to "q" but is configurable so the same primitive
// can drive other URL search filters in future phases.
"use client";

import {
  useEffect,
  useRef,
  useState,
  useTransition,
} from "react";
import {
  usePathname,
  useRouter,
  useSearchParams,
} from "next/navigation";
import { Input } from "@/components/ui/input";

const DEBOUNCE_MS = 300;

export function SearchInput({
  placeholder = "Search…",
  paramKey = "q",
}: {
  placeholder?: string;
  paramKey?: string;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const sp = useSearchParams();
  const [value, setValue] = useState(() => sp.get(paramKey) ?? "");
  const [, startTransition] = useTransition();
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clear any pending debounce timer when the component unmounts to
  // avoid a stale router.replace firing after navigation.
  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );

  function onChange(next: string) {
    setValue(next);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      const params = new URLSearchParams(sp.toString());
      if (next.length === 0) {
        params.delete(paramKey);
      } else {
        params.set(paramKey, next);
      }
      // Reset offset whenever the search term changes — avoids
      // landing on an empty page after the result set shrinks.
      params.delete("offset");
      const qs = params.toString();
      startTransition(() => {
        router.replace(qs ? `${pathname}?${qs}` : pathname, {
          scroll: false,
        });
      });
    }, DEBOUNCE_MS);
  }

  return (
    <Input
      type="search"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      aria-label={placeholder}
      className="w-full max-w-sm font-mono text-xs"
    />
  );
}
