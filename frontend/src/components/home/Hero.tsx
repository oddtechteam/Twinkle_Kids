import Image from "next/image";
import { ArrowRight } from "lucide-react";
import type { CSSProperties } from "react";

import { ButtonLink } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { Motif } from "@/components/ui/Motif";
import { isRenderableImage } from "@/lib/catalog/adapters";
import { HERO_MESSAGES } from "@/lib/content/fixtures/development-content";
import type { HeroSection } from "@/lib/content/types";
import styles from "./Hero.module.css";
import { HeroStage } from "./hero/HeroStage";

const reveal = (index: number) => ({ "--reveal-index": index }) as CSSProperties;

/**
 * Editorial split hero. Every word, image, link and theme comes from the CMS section. Without a
 * configured photo the right side shows the interactive podium stage.
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
          <p className={styles.body} data-reveal style={reveal(4)}>
            {section.body}
          </p>
          <div className={styles.ctas} data-reveal style={reveal(5)}>
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
            <ul className={styles.trust} data-reveal style={reveal(6)}>
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

        <div className={`${styles.visual} ${desktop ? "" : styles.stageVisual}`} data-reveal style={reveal(3)}>
          {desktop ? (
            <div className={styles.photoFrame}>
              {/* Art-directed crops: the CMS can supply a dedicated mobile image. */}
                <Image
                  src={desktop.src}
                  alt={desktop.alt}
                  fill
                  priority
                  sizes="(min-width: 960px) 46vw, 100vw"
                  className={`${styles.photo} ${mobile && mobile !== desktop ? styles.desktopOnly : ""}`}
                  style={{ objectPosition: desktop.focal ?? "50% 35%" }}
                />
                {mobile && mobile !== desktop && (
                  <Image
                    src={mobile.src}
                    alt={mobile.alt}
                    fill
                    priority
                    sizes="100vw"
                    className={`${styles.photo} ${styles.mobileOnly}`}
                    style={{ objectPosition: mobile.focal ?? "50% 35%" }}
                  />
                )}
            </div>
          ) : (
            <HeroStage messages={section.messages ?? HERO_MESSAGES} />
          )}
          {desktop && (
            <>
              <Motif kind="star" size={26} twinkle className={styles.floatA} />
              <Motif kind="heart" size={18} className={styles.floatB} />
              <Motif kind="star" size={14} twinkle className={styles.floatC} style={{ animationDelay: "1.4s" }} />
            </>
          )}
        </div>
      </div>
    </section>
  );
}
