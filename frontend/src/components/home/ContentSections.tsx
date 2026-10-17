import Image from "next/image";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { ProductArt } from "@/components/product/ProductArt";
import { ProductRail } from "@/components/product/ProductRail";
import { ButtonLink } from "@/components/ui/Button";
import { Accordion } from "@/components/ui/Form";
import { Motif } from "@/components/ui/Motif";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { cardFromSummary, isRenderableImage } from "@/lib/catalog/adapters";
import type {
  AnnouncementStripSection,
  FaqSection,
  OccasionSection,
  RichTextSection,
} from "@/lib/content/types";
import styles from "./ContentSections.module.css";

/** Plain text with blank-line paragraphs. CMS text is never rendered as HTML. */
function Paragraphs({ text }: { text: string }) {
  return (
    <>
      {text
        .split(/\n{2,}/)
        .map((p) => p.trim())
        .filter(Boolean)
        .map((p, i) => (
          <p key={i}>{p}</p>
        ))}
    </>
  );
}

export function FaqBlock({ section }: { section: FaqSection }) {
  return (
    <section className="section" aria-labelledby={`${section.id}-title`}>
      <div className="container-narrow">
        <SectionHeading id={`${section.id}-title`} title={section.title} align="center" />
        <div className={styles.faq}>
          {section.items.map((item, index) => (
            <Accordion key={`${index}-${item.question}`} title={item.question}>
              <div className={styles.prose}>
                <Paragraphs text={item.answer} />
              </div>
            </Accordion>
          ))}
        </div>
      </div>
    </section>
  );
}

export function AnnouncementStrip({ section }: { section: AnnouncementStripSection }) {
  return (
    <section className={`${styles.strip} ${styles[section.theme] ?? ""}`} aria-label="Announcement">
      <div className={`container ${styles.stripInner}`}>
        <Motif size={14} twinkle className={styles.stripStar} />
        <p className={styles.stripMessage}>{section.message}</p>
        {section.link && (
          <Link href={section.link.href} className={styles.stripLink}>
            {section.link.label}
            <ArrowRight aria-hidden="true" size={16} />
          </Link>
        )}
      </div>
    </section>
  );
}

export function RichTextBlock({ section }: { section: RichTextSection }) {
  return (
    <section className="section" aria-label={section.title ?? "Information"}>
      <div className={`container-narrow ${styles.rich} ${section.alignment === "left" ? styles.left : ""}`}>
        {section.title && <h2 className={styles.richTitle}>{section.title}</h2>}
        <div className={styles.prose}>
          <Paragraphs text={section.body} />
        </div>
      </div>
    </section>
  );
}

export function OccasionSpotlight({ section }: { section: OccasionSection }) {
  const image = section.image && isRenderableImage(section.image.src) ? section.image : null;
  return (
    <section className="section" aria-labelledby={`${section.id}-title`}>
      <div className="container">
        <div className={`${styles.occasion} ${styles[section.theme] ?? ""}`}>
          <div className={styles.occasionVisual}>
            {image ? (
              <Image
                src={image.src}
                alt={image.alt}
                fill
                sizes="(min-width: 960px) 40vw, 100vw"
                className={styles.occasionPhoto}
                style={{ objectPosition: image.focal ?? "50% 35%" }}
              />
            ) : (
              <ProductArt kind="dress" tone={section.theme === "navy" ? "navy" : "blush"} floating />
            )}
          </div>
          <div className={styles.occasionCopy}>
            {section.eyebrow && (
              <p className={styles.eyebrow}>
                <Motif size={12} /> {section.eyebrow}
              </p>
            )}
            <h2 id={`${section.id}-title`} className={styles.occasionTitle}>
              {section.title}
            </h2>
            {section.body && <p className={styles.occasionBody}>{section.body}</p>}
            {section.cta && (
              <ButtonLink
                href={section.cta.href}
                variant={section.theme === "navy" ? "accent" : "primary"}
                iconEnd={<ArrowRight aria-hidden="true" />}
              >
                {section.cta.label}
              </ButtonLink>
            )}
          </div>
        </div>
        {section.products.length > 0 && (
          <div className={styles.occasionProducts}>
            <ProductRail products={section.products.map(cardFromSummary)} label={section.title} />
          </div>
        )}
      </div>
    </section>
  );
}
