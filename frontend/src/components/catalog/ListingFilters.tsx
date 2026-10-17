"use client";

import { useRouter } from "next/navigation";
import { SlidersHorizontal } from "lucide-react";
import { useId, useState, useTransition } from "react";

import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { ChoiceChip, ColourSwatch, Select } from "@/components/ui/Form";
import {
  type ListingQuery,
  SORT_OPTIONS,
  activeFilterCount,
  listingHref,
  toggleValue,
} from "@/lib/catalog/query";
import type { ProductSort } from "@/lib/api/types";
import type { SiteContent } from "@/lib/content/types";
import styles from "./ListingFilters.module.css";

export type FilterOptions = Pick<SiteContent["catalog"], "filterSizes" | "filterColours" | "priceBands">;

interface Props {
  basePath: string;
  query: ListingQuery;
  options: FilterOptions;
}

function useListingNavigation(basePath: string, query: ListingQuery) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const go = (patch: Partial<ListingQuery>) =>
    startTransition(() => router.push(listingHref(basePath, query, patch), { scroll: false }));
  return { go, pending };
}

function FilterForm({ basePath, query, options }: Props) {
  const { go, pending } = useListingNavigation(basePath, query);
  const priceGroup = useId(); // sidebar and drawer forms each get their own radio group
  const activeBand = options.priceBands.findIndex(
    (band) => band.min === query.minPrice && band.max === query.maxPrice,
  );

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

      <fieldset className={styles.group}>
        <legend className={styles.legend}>Size</legend>
        <div className={styles.chips}>
          {options.filterSizes.map((size) => (
            <ChoiceChip
              key={size}
              label={size}
              checked={query.sizes.includes(size)}
              onChange={() => go({ sizes: toggleValue(query.sizes, size) })}
            />
          ))}
        </div>
      </fieldset>

      <fieldset className={styles.group}>
        <legend className={styles.legend}>Colour</legend>
        <div className={styles.swatches}>
          {options.filterColours.map((colour) => (
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

      <fieldset className={styles.group}>
        <legend className={styles.legend}>Price</legend>
        <div className={styles.bands}>
          <ChoiceChip
            type="radio"
            name={priceGroup}
            label="Any price"
            checked={activeBand === -1 && !query.minPrice && !query.maxPrice}
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

      {activeFilterCount(query) > 0 && (
        <Button
          variant="link"
          size="sm"
          onClick={() => go({ sizes: [], colours: [], minPrice: null, maxPrice: null, inStock: false })}
        >
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
