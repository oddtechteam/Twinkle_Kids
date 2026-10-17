import Image from "next/image";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

import { ProductArt, type ArtTone, artFor } from "@/components/product/ProductArt";
import { Skeleton } from "@/components/ui/Feedback";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { isRenderableImage } from "@/lib/catalog/adapters";
import { listCategories, topLevel } from "@/lib/catalog/api";
import type { CategoryShowcaseSection } from "@/lib/content/types";
import styles from "./CategoryShowcase.module.css";

const TILE_TONES: ArtTone[] = ["blush", "sky", "gold", "sage", "ivory", "navy"];

export async function CategoryShowcase({ section }: { section: CategoryShowcaseSection }) {
  let categories = section.categories; // CMS-selected, in CMS order
  if (!categories) {
    const result = await listCategories();
    categories = result.ok ? topLevel(result.data) : [];
  }
  categories = categories.slice(0, section.limit);
  if (categories.length === 0) return null;

  return (
    <section className="section" aria-labelledby={`${section.id}-title`}>
      <div className="container">
        <SectionHeading
          id={`${section.id}-title`}
          eyebrow={section.eyebrow}
          title={section.title}
          link={section.showViewAll === false ? undefined : { label: "Shop all", href: "/shop" }}
        />
        <ul className={`${styles.grid} ${styles[`count${Math.min(categories.length, 6)}`] ?? ""}`}>
          {categories.map((category, index) => {
            const art = artFor(category.slug, category.name);
            const tone = TILE_TONES[index % TILE_TONES.length]!;
            return (
              <li key={category.id} className={styles.item}>
                <Link href={`/category/${category.slug}`} className={`${styles.tile} ${styles[tone]}`}>
                  <span className={styles.visual}>
                    {category.image && isRenderableImage(category.image.url) ? (
                      <Image
                        src={category.image.url}
                        alt=""
                        fill
                        sizes="(min-width: 960px) 30vw, 50vw"
                        className={styles.photo}
                      />
                    ) : (
                      <ProductArt kind={art.kind} tone={tone} floating />
                    )}
                  </span>
                  <span className={styles.label}>
                    <span className={styles.name}>{category.name}</span>
                    <span className={styles.arrow} aria-hidden="true">
                      <ArrowUpRight size={18} strokeWidth={2.25} />
                    </span>
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}

export function CategoryShowcaseSkeleton() {
  return (
    <div className="section container" aria-hidden="true">
      <Skeleton width="16rem" height="2.25rem" radius="var(--radius-pill)" />
      <div className={styles.grid} style={{ marginTop: "var(--space-8)" }}>
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} height="16rem" radius="var(--radius-lg)" />
        ))}
      </div>
    </div>
  );
}
