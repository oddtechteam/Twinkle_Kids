import Image from "next/image";
import type { CSSProperties } from "react";
import { ArrowRight } from "lucide-react";

import { ButtonLink } from "@/components/ui/Button";
import { Motif } from "@/components/ui/Motif";
import { isRenderableImage } from "@/lib/catalog/adapters";
import type { PromoBannerSection } from "@/lib/content/types";
import styles from "./PromoBanner.module.css";
import { RevealOnView } from "./RevealOnView";

/**
 * Brand lookbook photo used until the admin sets a banner image in the homepage builder.
 * Decorative brand imagery only — not a product.
 */
const DEFAULT_PHOTO = {
  src: "/lookbook/lookbook-children.webp",
  alt: "A little girl in a blush-pink floral party dress beside a boy in a blue blazer",
};

const step = (index: number) => ({ "--step": index }) as CSSProperties;

/** Seasonal / festive editorial banner. */
export function PromoBanner({ section }: { section: PromoBannerSection }) {
  const cmsImage = section.image && isRenderableImage(section.image.src) ? section.image : null;
  const photo = cmsImage ?? DEFAULT_PHOTO;

  return (
    <section className="section" aria-labelledby={`${section.id}-title`}>
      <div className="container">
        <RevealOnView
          className={`${styles.banner} ${styles[section.theme] ?? ""} ${
            section.imagePosition === "left" ? styles.flip : ""
          }`}
        >
          <div className={styles.decor} aria-hidden="true">
            <span className={styles.glow} />
            <Motif size={18} twinkle className={styles.s1} />
            <Motif size={10} twinkle className={styles.s2} style={{ animationDelay: "1.2s" }} />
            <Motif size={14} twinkle className={styles.s3} style={{ animationDelay: "2.4s" }} />
            <Motif size={8} twinkle className={styles.s4} style={{ animationDelay: "3.1s" }} />
          </div>

          <div className={styles.copy}>
            {section.eyebrow && (
              <p className={`${styles.eyebrow} ${styles.rise}`} style={step(0)}>
                <span className={styles.rule} aria-hidden="true" />
                {section.eyebrow}
              </p>
            )}
            <h2 id={`${section.id}-title`} className={`${styles.title} ${styles.rise}`} style={step(1)}>
              {section.title}
            </h2>
            {section.body && (
              <p className={`${styles.body} ${styles.rise}`} style={step(2)}>
                {section.body}
              </p>
            )}
            {section.cta && (
              <div className={styles.rise} style={step(3)}>
                <ButtonLink
                  href={section.cta.href}
                  size="lg"
                  variant={section.theme === "navy" ? "accent" : "primary"}
                  iconEnd={<ArrowRight aria-hidden="true" />}
                >
                  {section.cta.label}
                </ButtonLink>
              </div>
            )}
          </div>

          <div className={styles.visual}>
            <span className={styles.halo} aria-hidden="true" />
            <div className={styles.photoFrame}>
              <Image
                src={photo.src}
                alt={photo.alt}
                fill
                sizes="(min-width: 960px) 26rem, (min-width: 600px) 22rem, 80vw"
                className={`${styles.photo} ${cmsImage ? "" : styles.defaultPhoto}`}
              />
            </div>
            <span className={`${styles.card} ${styles.cardTop}`} aria-hidden="true">
              <Image src="/lookbook/lookbook-dress.webp" alt="" fill sizes="96px" className={styles.cardImage} />
            </span>
            <span className={`${styles.card} ${styles.cardBottom}`} aria-hidden="true">
              <Image src="/lookbook/lookbook-outfit.webp" alt="" fill sizes="96px" className={styles.cardImage} />
            </span>
            <Motif size={16} twinkle className={styles.frameStar} style={{ animationDelay: "0.6s" }} />
          </div>
        </RevealOnView>
      </div>
    </section>
  );
}
