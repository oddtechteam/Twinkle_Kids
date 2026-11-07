import Image from "next/image";
import Link from "next/link";
import type { CSSProperties } from "react";
import { ArrowRight } from "lucide-react";

import { ProductArt, type ArtTone, artFor } from "@/components/product/ProductArt";
import { Motif } from "@/components/ui/Motif";
import { Skeleton } from "@/components/ui/Feedback";
import { isRenderableImage } from "@/lib/catalog/adapters";
import { listCategories, topLevel } from "@/lib/catalog/api";
import type { CategoryShowcaseSection } from "@/lib/content/types";
import { framedImage } from "@/lib/media/frames";
import styles from "./CategoryShowcase.module.css";
import { RevealOnView } from "./RevealOnView";

const TILE_TONES: ArtTone[] = ["blush", "sky", "gold", "sage", "ivory", "navy"];

/**
 * Admin crops are already framed for the square tile, so they sit centred. Uncropped originals
 * lean slightly upwards: children's faces usually live in the top third of a fashion photo.
 */
const CROPPED_POSITION = "50% 50%";
const ORIGINAL_POSITION = "50% 30%";

const step = (index: number) => ({ "--step": index }) as CSSProperties;

export async function CategoryShowcase({ section }: { section: CategoryShowcaseSection }) {
  let categories = section.categories; // CMS-selected, in CMS order
  if (!categories) {
    const result = await listCategories();
    categories = result.ok ? topLevel(result.data) : [];
  }
  categories = categories.slice(0, section.limit);
  if (categories.length === 0) return null;

  const titleId = `${section.id}-title`;
  return (
    <section className={`section ${styles.section}`} aria-labelledby={titleId}>
      <RevealOnView className={`container ${styles.inner}`}>
        <div className={styles.decor} aria-hidden="true">
          {/* The span drifts; the motif inside keeps its own twinkle. */}
          <span className={styles.d1}>
            <Motif size={16} twinkle color="var(--tk-gold)" />
          </span>
          <span className={styles.d2}>
            <Motif size={10} twinkle color="var(--tk-gold)" style={{ animationDelay: "1.4s" }} />
          </span>
          <span className={styles.d3}>
            <Motif kind="heart" size={11} color="var(--tk-coral)" />
          </span>
          <span className={styles.d4}>
            <Motif size={12} twinkle color="var(--tk-gold)" style={{ animationDelay: "2.6s" }} />
          </span>
        </div>

        <header className={styles.head}>
          <div className={styles.headText}>
            {section.eyebrow && (
              <p className={`${styles.eyebrow} ${styles.rise}`} style={step(0)}>
                <Motif size={11} className={styles.eyebrowStar} />
                {section.eyebrow}
              </p>
            )}
            <h2 id={titleId} className={`${styles.title} ${styles.rise}`} style={step(1)}>
              {section.title}
            </h2>
          </div>
          {section.showViewAll !== false && (
            <Link href="/shop" className={`${styles.viewAll} ${styles.rise}`} style={step(2)}>
              Shop all
              <span className={styles.viewAllIcon} aria-hidden="true">
                <ArrowRight size={16} strokeWidth={2.25} />
              </span>
            </Link>
          )}
        </header>

        <ul className={styles.grid}>
          {categories.map((category, index) => {
            const art = artFor(category.slug, category.name);
            const tone = TILE_TONES[index % TILE_TONES.length]!;
            const cropped = Boolean(category.image?.crops?.category);
            const photo = category.image ? framedImage(category.image, "category").url : null;
            return (
              <li key={category.id} className={`${styles.item} ${styles.card}`} style={step(index + 2)}>
                <Link href={`/category/${category.slug}`} className={`${styles.tile} ${styles[tone]}`}>
                  <span className={styles.frame}>
                    {photo && isRenderableImage(photo) ? (
                      <Image
                        src={photo}
                        alt=""
                        fill
                        sizes="(min-width: 900px) 24vw, 46vw"
                        className={styles.photo}
                        style={{ objectPosition: cropped ? CROPPED_POSITION : ORIGINAL_POSITION }}
                      />
                    ) : (
                      <span className={styles.art}>
                        <ProductArt kind={art.kind} tone={tone} floating />
                      </span>
                    )}
                    <span className={styles.shade} aria-hidden="true" />
                    <span className={styles.index} aria-hidden="true">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <span className={styles.label}>
                      <span className={styles.name}>{category.name}</span>
                      <span className={styles.explore} aria-hidden="true">
                        <span className={styles.exploreText}>Explore</span>
                        <span className={styles.arrow}>
                          <ArrowRight size={16} strokeWidth={2.25} />
                        </span>
                      </span>
                    </span>
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      </RevealOnView>
    </section>
  );
}

export function CategoryShowcaseSkeleton() {
  return (
    <div className="section container" aria-hidden="true">
      <Skeleton width="16rem" height="2.25rem" radius="var(--radius-pill)" />
      <div className={styles.grid} style={{ marginTop: "var(--space-8)" }}>
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} className={styles.skeletonTile} radius="var(--radius-xl)" />
        ))}
      </div>
    </div>
  );
}
