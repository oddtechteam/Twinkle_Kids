import Link from "next/link";
import { RotateCcw, X } from "lucide-react";
import type { ReactNode } from "react";

import { ProductGrid, ProductGridSkeleton } from "@/components/product/ProductGrid";
import { type Crumb, Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { ButtonLink } from "@/components/ui/Button";
import { EmptyState, Skeleton } from "@/components/ui/Feedback";
import { Motif } from "@/components/ui/Motif";
import type { ApiResult, ProductList } from "@/lib/api/types";
import { cardFromSummary } from "@/lib/catalog/adapters";
import { type ListingQuery, CLEARED_FILTERS, activeFilterCount, listingHref } from "@/lib/catalog/query";
import { formatMoney, plural } from "@/lib/format";
import { type FilterOptions, FilterDrawer, FilterSidebar, SortSelect } from "./ListingFilters";
import { Pagination } from "./Pagination";
import styles from "./ListingView.module.css";

interface ListingViewProps {
  title: string;
  eyebrow?: string;
  description?: string | null;
  breadcrumbs: Crumb[];
  basePath: string;
  query: ListingQuery;
  result: ApiResult<ProductList>;
  options: FilterOptions;
  /** Optional row of links under the heading (sub-categories, suggestions). */
  related?: { label: string; href: string }[];
  emptyMessage?: { title: string; description: string };
  headerExtra?: ReactNode;
}

export function ListingView({
  title,
  eyebrow,
  description,
  breadcrumbs,
  basePath,
  query,
  result,
  options,
  related = [],
  emptyMessage,
  headerExtra,
}: ListingViewProps) {
  const total = result.ok ? result.data.total : 0;
  const filtered = activeFilterCount(query) > 0;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className="container">
          <Breadcrumbs items={breadcrumbs} />
          <div className={styles.headingRow}>
            <div className={styles.heading}>
              {eyebrow && (
                <p className={styles.eyebrow}>
                  <Motif size={12} /> {eyebrow}
                </p>
              )}
              <h1 className={styles.title}>{title}</h1>
              {description && <p className={styles.description}>{description}</p>}
            </div>
            {headerExtra}
          </div>
          {related.length > 0 && (
            <ul className={styles.related} aria-label="Related categories">
              {related.map((link) => (
                <li key={link.href}>
                  <Link href={link.href} className={styles.relatedLink}>
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </header>

      <div className={`container ${styles.layout}`}>
        <FilterSidebar basePath={basePath} query={query} options={options} />

        <div className={styles.results}>
          <div className={styles.toolbar}>
            <p className={styles.count} aria-live="polite">
              {result.ok ? plural(total, "style") : " "}
            </p>
            <div className={styles.toolbarActions}>
              <FilterDrawer basePath={basePath} query={query} options={options} total={total} />
              <SortSelect basePath={basePath} query={query} />
            </div>
          </div>

          <ActiveFilters basePath={basePath} query={query} options={options} />

          {!result.ok ? (
            <EmptyState
              tone="error"
              title="We couldn't load these styles"
              description="The catalogue is taking a little longer than usual. Please try again in a moment."
              action={
                <ButtonLink href={listingHref(basePath, query, { page: query.page })} iconStart={<RotateCcw aria-hidden="true" />}>
                  Try again
                </ButtonLink>
              }
            />
          ) : result.data.items.length === 0 ? (
            <EmptyState
              title={filtered ? "No styles match these filters" : (emptyMessage?.title ?? "No styles here yet")}
              description={
                filtered
                  ? "Try removing a filter or two to see more of the collection."
                  : (emptyMessage?.description ?? "New styles are on their way — check back soon.")
              }
              action={
                filtered ? (
                  <ButtonLink href={listingHref(basePath, query, CLEARED_FILTERS)}>
                    Clear filters
                  </ButtonLink>
                ) : (
                  <ButtonLink href="/shop">Browse all styles</ButtonLink>
                )
              }
            />
          ) : (
            <>
              <ProductGrid products={result.data.items.map(cardFromSummary)} columns={3} priorityCount={3} />
              <Pagination basePath={basePath} query={query} pages={result.data.pages} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function ActiveFilters({ basePath, query, options }: { basePath: string; query: ListingQuery; options: FilterOptions }) {
  const named = (list: { label: string; slug: string }[], slug: string) =>
    list.find((item) => item.slug === slug)?.label ?? slug;
  const chips: { label: string; href: string }[] = [
    ...(query.category
      ? [{ label: named(options.categories, query.category), href: listingHref(basePath, query, { category: null }) }]
      : []),
    ...(query.collection
      ? [{ label: named(options.collections, query.collection), href: listingHref(basePath, query, { collection: null }) }]
      : []),
    ...query.sizes.map((size) => ({
      label: `Size ${size}`,
      href: listingHref(basePath, query, { sizes: query.sizes.filter((s) => s !== size) }),
    })),
    ...query.colours.map((colour) => ({
      label: colour,
      href: listingHref(basePath, query, { colours: query.colours.filter((c) => c !== colour) }),
    })),
  ];
  if (query.minPrice || query.maxPrice) {
    const label =
      query.minPrice && query.maxPrice
        ? `${formatMoney(query.minPrice)} – ${formatMoney(query.maxPrice)}`
        : query.minPrice
          ? `From ${formatMoney(query.minPrice)}`
          : `Up to ${formatMoney(query.maxPrice ?? "0")}`;
    chips.push({ label, href: listingHref(basePath, query, { minPrice: null, maxPrice: null }) });
  }
  if (query.inStock) {
    chips.push({ label: "In stock", href: listingHref(basePath, query, { inStock: false }) });
  }
  if (chips.length === 0) return null;

  return (
    <ul className={styles.active} aria-label="Active filters">
      {chips.map((chip) => (
        <li key={chip.label}>
          <Link href={chip.href} className={styles.activeChip} aria-label={`Remove filter: ${chip.label}`} scroll={false}>
            {chip.label}
            <X aria-hidden="true" size={14} strokeWidth={2.5} />
          </Link>
        </li>
      ))}
      {chips.length > 1 && (
        <li>
          <Link href={listingHref(basePath, query, CLEARED_FILTERS)} className={styles.clearAll} scroll={false}>
            Clear all
          </Link>
        </li>
      )}
    </ul>
  );
}

export function ListingSkeleton() {
  return (
    <div className={styles.page} aria-busy="true" aria-label="Loading styles">
      <header className={styles.header}>
        <div className="container">
          <Skeleton width="10rem" height="0.9rem" />
          <div style={{ marginTop: "var(--space-5)" }}>
            <Skeleton width="min(22rem, 80%)" height="2.75rem" radius="var(--radius-pill)" />
          </div>
        </div>
      </header>
      <div className={`container ${styles.layout}`}>
        <div className={styles.skeletonSidebar}>
          <Skeleton height="14rem" radius="var(--radius-lg)" />
        </div>
        <div className={styles.results}>
          <div className={styles.toolbar}>
            <Skeleton width="6rem" height="1rem" />
            <Skeleton width="12rem" height="2.75rem" radius="var(--radius-pill)" />
          </div>
          <ProductGridSkeleton count={6} columns={3} />
        </div>
      </div>
    </div>
  );
}
