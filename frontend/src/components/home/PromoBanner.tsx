import Image from "next/image";
import { ArrowRight } from "lucide-react";

import { ProductArt } from "@/components/product/ProductArt";
import { ButtonLink } from "@/components/ui/Button";
import { Motif } from "@/components/ui/Motif";
import { isRenderableImage } from "@/lib/catalog/adapters";
import type { PromoBannerSection } from "@/lib/content/types";
import styles from "./PromoBanner.module.css";

/** Seasonal / festive editorial banner. */
export function PromoBanner({ section }: { section: PromoBannerSection }) {
  const image = section.image && isRenderableImage(section.image.src) ? section.image : null;
  return (
    <section className="section" aria-labelledby={`${section.id}-title`}>
      <div className="container">
        <div
          className={`${styles.banner} ${styles[section.theme] ?? ""} ${
            section.imagePosition === "left" ? styles.flip : ""
          }`}
        >
          <div className={styles.sparkles} aria-hidden="true">
            <Motif size={18} twinkle className={styles.s1} />
            <Motif size={10} twinkle className={styles.s2} style={{ animationDelay: "0.8s" }} />
            <Motif size={14} twinkle className={styles.s3} style={{ animationDelay: "1.6s" }} />
            <Motif kind="heart" size={12} className={styles.s4} />
          </div>

          <div className={styles.copy}>
            {section.eyebrow && <p className={styles.eyebrow}>{section.eyebrow}</p>}
            <h2 id={`${section.id}-title`} className={styles.title}>
              {section.title}
            </h2>
            {section.body && <p className={styles.body}>{section.body}</p>}
            {section.cta && (
              <ButtonLink
                href={section.cta.href}
                size="lg"
                variant={section.theme === "navy" ? "accent" : "primary"}
                iconEnd={<ArrowRight aria-hidden="true" />}
              >
                {section.cta.label}
              </ButtonLink>
            )}
          </div>

          <div className={styles.visual}>
            {image ? (
              <div className={styles.photoFrame}>
                <Image src={image.src} alt={image.alt} fill sizes="(min-width: 960px) 40vw, 90vw" className={styles.photo} />
              </div>
            ) : (
              <div className={styles.artStack} aria-hidden="true">
                <span className={styles.artBack}>
                  <ProductArt kind="skirt" tone="gold" floating />
                </span>
                <span className={styles.artFront}>
                  <ProductArt kind="dress" tone="blush" floating />
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
