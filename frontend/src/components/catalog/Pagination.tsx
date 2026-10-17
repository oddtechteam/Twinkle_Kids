import Link from "next/link";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { type ListingQuery, listingHref } from "@/lib/catalog/query";
import styles from "./Pagination.module.css";

function pageWindow(current: number, total: number): (number | "gap")[] {
  const pages = new Set([1, total, current - 1, current, current + 1].filter((p) => p >= 1 && p <= total));
  const sorted = [...pages].sort((a, b) => a - b);
  const out: (number | "gap")[] = [];
  sorted.forEach((page, index) => {
    const previous = sorted[index - 1];
    if (previous !== undefined && page - previous > 1) out.push("gap");
    out.push(page);
  });
  return out;
}

/** Crawlable, link-based pagination (works without JavaScript). */
export function Pagination({
  basePath,
  query,
  pages,
}: {
  basePath: string;
  query: ListingQuery;
  pages: number;
}) {
  if (pages <= 1) return null;
  const current = Math.min(query.page, pages);
  const href = (page: number) => listingHref(basePath, query, { page });

  return (
    <nav aria-label="Pagination" className={styles.nav}>
      {current > 1 ? (
        <Link href={href(current - 1)} className={styles.step} rel="prev">
          <ChevronLeft aria-hidden="true" size={18} /> <span>Previous</span>
        </Link>
      ) : (
        <span className={`${styles.step} ${styles.disabled}`} aria-hidden="true">
          <ChevronLeft size={18} /> <span>Previous</span>
        </span>
      )}

      <ol className={styles.pages}>
        {pageWindow(current, pages).map((page, index) =>
          page === "gap" ? (
            <li key={`gap-${index}`} className={styles.gap} aria-hidden="true">
              …
            </li>
          ) : (
            <li key={page}>
              <Link
                href={href(page)}
                className={`${styles.page} ${page === current ? styles.current : ""}`}
                aria-current={page === current ? "page" : undefined}
                aria-label={`Page ${page}`}
              >
                {page}
              </Link>
            </li>
          ),
        )}
      </ol>

      {current < pages ? (
        <Link href={href(current + 1)} className={styles.step} rel="next">
          <span>Next</span> <ChevronRight aria-hidden="true" size={18} />
        </Link>
      ) : (
        <span className={`${styles.step} ${styles.disabled}`} aria-hidden="true">
          <span>Next</span> <ChevronRight size={18} />
        </span>
      )}
    </nav>
  );
}
