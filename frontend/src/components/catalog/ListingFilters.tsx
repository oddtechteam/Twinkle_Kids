"use client";

import { useRouter } from "next/navigation";
import { SlidersHorizontal } from "lucide-react";
import { useId, useState, useTransition } from "react";

import { useNavigationProgress } from "@/components/layout/NavigationProgress";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { ChoiceChip, ColourSwatch, Select } from "@/components/ui/Form";
import type { FilterOptions } from "@/lib/catalog/filters";
import {
  type ListingQuery,
  CLEARED_FILTERS,
  SORT_OPTIONS,
  activeFilterCount,
  listingHref,
  toggleValue,
} from "@/lib/catalog/query";
import type { ProductSort } from "@/lib/api/types";
import styles from "./ListingFilters.module.css";

export type { FilterOptions } from "@/lib/catalog/filters";

interface Props {
  basePath: string;
  query: ListingQuery;
  options: FilterOptions;
}

function useListingNavigation(basePath: string, query: ListingQuery) {
  const router = useRouter();
  const progress = useNavigationProgress();
  const [pending, startTransition] = useTransition();
  const go = (patch: Partial<ListingQuery>) => {
    const href = listingHref(basePath, query, patch);
    progress.start(href);
    startTransition(() => router.push(href, { scroll: false }));
  };
  return { go, pending };
}

function FilterForm({ basePath, query, options }: Props) {
  const { go, pending } = useListingNavigation(basePath, query);
  // Sidebar and drawer render this form at the same time: every radio group needs its own name.
  const priceGroup = useId();
  const categoryGroup = useId();
  const collectionGroup = useId();
  const activeBand = options.priceBands.findIndex(
    (band) => band.min === query.minPrice && band.max === query.maxPrice,
  );
  const customPrice = activeBand === -1 && Boolean(query.minPrice || query.maxPrice);

  return (
    <div className={styles.form} aria-busy={pending}>
      <fieldset className={styles.group}>
        <legend className={styles.legend}>Availability</legend>
        <ChoiceChip
          label="In stock only"
          checked={query.inStock}
          onChange={() => go({ inStock: !query.inStock })}
        />
      </fieldset>

      {options.categories.length > 0 && (
        <fieldset className={styles.group}>
          <legend className={styles.legend}>Category</legend>
          <div className={styles.bands}>
            <ChoiceChip
              type="radio"
              name={categoryGroup}
              label="All categories"
              checked={query.category === null}
              onChange={() => go({ category: null })}
            />
            {options.categories.map((category) => (
              <ChoiceChip
                key={category.slug}
                type="radio"
                name={categoryGroup}
                label={category.label}
                checked={query.category === category.slug}
                onChange={() => go({ category: category.slug })}
              />
            ))}
          </div>
        </fieldset>
      )}

      {options.collections.length > 0 && (
        <fieldset className={styles.group}>
          <legend className={styles.legend}>Collection</legend>
          <div className={styles.bands}>
            <ChoiceChip
              type="radio"
              name={collectionGroup}
              label="All collections"
              checked={query.collection === null}
              onChange={() => go({ collection: null })}
            />
            {options.collections.map((collection) => (
              <ChoiceChip
                key={collection.slug}
                type="radio"
                name={collectionGroup}
                label={collection.label}
                checked={query.collection === collection.slug}
                onChange={() => go({ collection: collection.slug })}
              />
            ))}
          </div>
        </fieldset>
      )}

      {options.sizes.length > 0 && (
        <fieldset className={styles.group}>
          <legend className={styles.legend}>Size</legend>
          <div className={styles.chips}>
            {options.sizes.map((size) => (
              <ChoiceChip
                key={size}
                label={size}
                checked={query.sizes.includes(size)}
                onChange={() => go({ sizes: toggleValue(query.sizes, size) })}
              />
            ))}
          </div>
        </fieldset>
      )}

      {options.colours.length > 0 && (
        <fieldset className={styles.group}>
          <legend className={styles.legend}>Colour</legend>
          <div className={styles.swatches}>
            {options.colours.map((colour) => (
              <ColourSwatch
                key={colour.name}
                type="checkbox"
                colourName={colour.name}
                hex={colour.hex}
                showLabel
                checked={query.colours.includes(colour.name)}
                onChange={() => go({ colours: toggleValue(query.colours, colour.name) })}
              />
            ))}
          </div>
        </fieldset>
      )}

      {(options.priceBands.length > 0 || customPrice) && (
        <fieldset className={styles.group}>
          <legend className={styles.legend}>Price</legend>
          <div className={styles.bands}>
            <ChoiceChip
              type="radio"
              name={priceGroup}
              label="Any price"
              checked={!query.minPrice && !query.maxPrice}
              onChange={() => go({ minPrice: null, maxPrice: null })}
            />
            {options.priceBands.map((band, index) => (
              <ChoiceChip
                key={band.label}
                type="radio"
                name={priceGroup}
                label={band.label}
                checked={activeBand === index}
                onChange={() => go({ minPrice: band.min, maxPrice: band.max })}
              />
            ))}
          </div>
        </fieldset>
      )}

      {activeFilterCount(query) > 0 && (
        <Button variant="link" size="sm" onClick={() => go(CLEARED_FILTERS)}>
          Clear all filters
        </Button>
      )}
      <p className="visually-hidden" aria-live="polite">
        {pending ? "Updating results" : ""}
      </p>
    </div>
  );
}

/** Sticky sidebar on large screens. */
export function FilterSidebar(props: Props) {
  return (
    <aside className={styles.sidebar} aria-label="Filters">
      <h2 className={styles.sidebarTitle}>Filter</h2>
      <FilterForm {...props} />
    </aside>
  );
}

/** "Filters" button + drawer on small screens. */
export function FilterDrawer(props: Props & { total: number }) {
  const [open, setOpen] = useState(false);
  const count = activeFilterCount(props.query);
  return (
    <>
      <Button
        variant="soft"
        size="sm"
        className={styles.drawerButton}
        iconStart={<SlidersHorizontal aria-hidden="true" />}
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
      >
        Filters{count > 0 ? ` (${count})` : ""}
      </Button>
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        title="Filter"
        variant="drawer-end"
        footer={
          <Button fullWidth onClick={() => setOpen(false)}>
            Show {props.total} {props.total === 1 ? "style" : "styles"}
          </Button>
        }
      >
        <FilterForm {...props} />
      </Dialog>
    </>
  );
}

export function SortSelect({ basePath, query }: { basePath: string; query: ListingQuery }) {
  const { go, pending } = useListingNavigation(basePath, query);
  return (
    <Select
      label="Sort by"
      hideLabel
      className={styles.sort}
      value={query.sort}
      disabled={pending}
      onChange={(event) => go({ sort: event.target.value as ProductSort })}
    >
      {SORT_OPTIONS.map((option) => (
        <option key={option.value} value={option.value}>
          Sort: {option.label}
        </option>
      ))}
    </Select>
  );
}
