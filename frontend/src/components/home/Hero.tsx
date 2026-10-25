import { ArrowRight } from "lucide-react";
import type { CSSProperties } from "react";

import { ButtonLink } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { Motif } from "@/components/ui/Motif";
import { isRenderableImage } from "@/lib/catalog/adapters";
import type { HeroSection } from "@/lib/content/types";
import styles from "./Hero.module.css";
import { FloatingLookbook } from "./hero/FloatingLookbook";

const reveal = (index: number) => ({ "--reveal-index": index }) as CSSProperties;

/**
 * Editorial split hero: CMS copy on one side, the Floating Lookbook on the other. Every word,
 * link and theme comes from the CMS section; a configured photo replaces the lookbook's art.
 */
export function Hero({ section }: { section: HeroSection }) {
  const { headline } = section;
  const desktop = section.image && isRenderableImage(section.image.src) ? section.image : null;
  const mobile = section.mobileImage && isRenderableImage(section.mobileImage.src) ? section.mobileImage : desktop;

  return (
    <section
      className={`${styles.hero} ${styles[section.theme] ?? ""} ${section.layout === "image-left" ? styles.flip : ""}`}
      aria-labelledby={`${section.id}-title`}
    >
      <div className={styles.backdrop} aria-hidden="true">
        <span className={styles.blobA} />
        <span className={styles.blobB} />
      </div>

      <div className={`container ${styles.grid}`}>
        <div className={styles.copy}>
          {section.eyebrow && (
            <p className={styles.eyebrow} data-reveal style={reveal(0)}>
              <Motif size={14} twinkle />
              {section.eyebrow}
            </p>
          )}
          <h1 id={`${section.id}-title`} className={styles.title}>
            <span className={styles.lead} data-reveal style={reveal(1)}>
              {headline.lead}
            </span>{" "}
            {headline.highlight && (
              <span className={styles.line} data-reveal style={reveal(2)}>
                <span className={styles.highlight}>
                  {headline.highlight}
                  <svg viewBox="0 0 300 24" className={styles.swash} aria-hidden="true" preserveAspectRatio="none">
                    <path d="M4 17C70 6 150 4 296 13" />
                  </svg>
                </span>
                {headline.trail && <> {headline.trail}</>}
              </span>
            )}
          </h1>
          <p className={styles.body} data-reveal style={reveal(3)}>
            {section.body}
          </p>
          <div className={styles.ctas} data-reveal style={reveal(4)}>
            {section.primaryCta && (
              <ButtonLink
                href={section.primaryCta.href}
                size="lg"
                variant={section.theme === "navy" ? "accent" : "primary"}
                iconEnd={<ArrowRight aria-hidden="true" />}
                className={styles.primary}
              >
                {section.primaryCta.label}
              </ButtonLink>
            )}
            {section.secondaryCta && (
              <ButtonLink href={section.secondaryCta.href} size="lg" variant="outline" className={styles.secondary}>
                {section.secondaryCta.label}
              </ButtonLink>
            )}
          </div>
          {section.trust.length > 0 && (
            <ul className={styles.trust} data-reveal style={reveal(5)}>
              {section.trust.map((item) => (
                <li key={item.label}>
                  <span className={styles.trustIcon}>
                    <Icon name={item.icon} size={16} />
                  </span>
                  {item.label}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className={styles.visual}>
          <FloatingLookbook image={desktop} mobileImage={mobile} />
        </div>
      </div>
    </section>
  );
}
