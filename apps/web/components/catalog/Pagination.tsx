// C5 / R3 Pagination follow-up:
// - Disabled boundaries render <span aria-disabled>, NOT <a href="#">.
//   `aria-disabled` is advisory; an `<a href="#">` would still
//   navigate on Tab+Enter.
// - Adjacent items wrapped in <React.Fragment>, NOT <span>, so the
//   resulting DOM is <ul><li>...</li><li>...</li></ul> (valid HTML)
//   instead of <ul><span><li>...</li></span></ul> (invalid).
import * as React from "react";
import {
  Pagination as Shell,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
  PaginationEllipsis,
} from "@/components/ui/pagination";

export function Pagination({
  total,
  limit,
  offset,
  hrefBase,
  searchParams,
}: {
  total: number;
  limit: number;
  offset: number;
  hrefBase: string;
  searchParams: URLSearchParams;
}) {
  const totalPages = Math.max(1, Math.ceil(total / limit));
  const currentPage = Math.floor(offset / limit) + 1;
  const prevDisabled = offset === 0;
  const nextDisabled = offset + limit >= total;

  function urlFor(page: number) {
    const sp = new URLSearchParams(searchParams);
    sp.set("offset", String((page - 1) * limit));
    sp.set("limit", String(limit));
    return `${hrefBase}?${sp.toString()}`;
  }

  // Window pages: first, current-1, current, current+1, last.
  const pages = new Set<number>([
    1,
    totalPages,
    currentPage - 1,
    currentPage,
    currentPage + 1,
  ]);
  const sortedPages = [...pages]
    .filter((p) => p >= 1 && p <= totalPages)
    .sort((a, b) => a - b);

  return (
    <Shell>
      <PaginationContent>
        {prevDisabled ? (
          <PaginationItem>
            <span
              aria-disabled="true"
              aria-label="No previous page"
              className="inline-flex select-none items-center px-3 py-2 opacity-40"
            >
              ‹ Prev
            </span>
          </PaginationItem>
        ) : (
          <PaginationItem>
            <PaginationPrevious href={urlFor(currentPage - 1)} />
          </PaginationItem>
        )}

        {sortedPages.map((p, i) => {
          const prev = sortedPages[i - 1];
          const needsEllipsis = prev !== undefined && p - prev > 1;
          return (
            <React.Fragment key={p}>
              {needsEllipsis ? (
                <PaginationItem>
                  <PaginationEllipsis />
                </PaginationItem>
              ) : null}
              <PaginationItem>
                <PaginationLink
                  href={urlFor(p)}
                  isActive={p === currentPage}
                >
                  {p}
                </PaginationLink>
              </PaginationItem>
            </React.Fragment>
          );
        })}

        {nextDisabled ? (
          <PaginationItem>
            <span
              aria-disabled="true"
              aria-label="No next page"
              className="inline-flex select-none items-center px-3 py-2 opacity-40"
            >
              Next ›
            </span>
          </PaginationItem>
        ) : (
          <PaginationItem>
            <PaginationNext href={urlFor(currentPage + 1)} />
          </PaginationItem>
        )}
      </PaginationContent>
    </Shell>
  );
}
