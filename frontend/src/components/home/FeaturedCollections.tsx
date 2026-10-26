import Image from "next/image";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { ProductArt } from "@/components/product/ProductArt";
import { Motif } from "@/components/ui/Motif";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { isRenderableImage } from "@/lib/catalog/adapters";
import type { FeaturedCollectionsSection } from "@/lib/content/types";
import styles from "./FeaturedCollections.module.css";

const ART_TONE = { navy: "navy", blush: "blush", gold: "gold", ivory: "ivory" } as const;

export function FeaturedCollections({ section }: { section: FeaturedCollectionsSection }) {
  return (
    <section className="section" aria-labelledby={`${section.id}-title`}>
      <div className="container">
        <SectionHeading id={`${section.id}-title`} eyebrow={section.eyebrow} title={section.title} align="center" />
        <ul className={styles.grid}>
          {section.items.map((item, index) => (
            <li key={item.href} className={styles.item}>
              <Link href={item.href} className={`${styles.tile} ${styles[item.theme] ?? ""}`}>
                <span className={styles.visual}>
                  {item.image && isRenderableImage(item.image.src) ? (
                    <Image
                      src={item.image.src}
                      alt=""
                      fill
                      sizes="(min-width: 1100px) 33vw, (min-width: 760px) 50vw, 100vw"
                      className={styles.photo}
                      style={{ objectPosition: item.image.focal ?? "50% 40%" }}
                    />
                  ) : (
                    <ProductArt kind={item.art} tone={ART_TONE[item.theme]} floating />
                  )}
                </span>
                <span className={styles.content}>
                  <span className={styles.index} aria-hidden="true">
                    <Motif size={12} /> 0{index + 1}
                  </span>
                  <span className={styles.title}>{item.title}</span>
                  {item.caption && <span className={styles.caption}>{item.caption}</span>}
                  <span className={styles.cta}>
                    Explore <ArrowRight aria-hidden="true" size={16} strokeWidth={2.25} />
                  </span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
