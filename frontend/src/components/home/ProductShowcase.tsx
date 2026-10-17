import { ProductGrid, ProductGridSkeleton } from "@/components/product/ProductGrid";
import { ProductRail } from "@/components/product/ProductRail";
import { Skeleton } from "@/components/ui/Feedback";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { cardFromSummary } from "@/lib/catalog/adapters";
import { selectProducts } from "@/lib/catalog/api";
import type { ProductRailSection } from "@/lib/content/types";
import styles from "./ProductShowcase.module.css";

/** A CMS-configured product selection (new arrivals, favourites, a category or collection). */
export async function ProductShowcase({ section }: { section: ProductRailSection }) {
  // CMS sections arrive with products resolved in that section's own order; fixture sections
  // select products by rule.
  let items = section.products;
  if (!items && section.selection) {
    const result = await selectProducts(section.selection);
    items = result.ok ? result.data.items : [];
  }
  // Nothing to show (or the catalogue is unreachable): the section quietly steps aside.
  if (!items || items.length === 0) return null;
  const products = items.map(cardFromSummary);

  return (
    <section
      className={`section ${styles.section} ${styles[section.theme] ?? ""}`}
      aria-labelledby={`${section.id}-title`}
    >
      <div className="container">
        <SectionHeading
          id={`${section.id}-title`}
          eyebrow={section.eyebrow}
          title={section.title}
          subtitle={section.subtitle}
          link={section.cta}
        />
        {section.layout === "carousel" ? (
          <ProductRail products={products} label={section.title} />
        ) : (
          <ProductGrid products={products} />
        )}
      </div>
    </section>
  );
}

export function ProductShowcaseSkeleton() {
  return (
    <div className="section container" aria-hidden="true">
      <Skeleton width="14rem" height="2.25rem" radius="var(--radius-pill)" />
      <div style={{ marginTop: "var(--space-8)" }}>
        <ProductGridSkeleton count={4} />
      </div>
    </div>
  );
}
