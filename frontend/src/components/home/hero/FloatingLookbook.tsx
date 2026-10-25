import Image from "next/image";
import { Crown, Gift, Heart, ShoppingBag, Star, type LucideIcon } from "lucide-react";
import type { CSSProperties } from "react";

import { Motif } from "@/components/ui/Motif";
import type { MediaRef } from "@/lib/content/types";
import styles from "./FloatingLookbook.module.css";

/**
 * Floating Lookbook: the children in a blush arch with coordinated looks floating around them.
 * Art comes from /public/twinkle-kids-floating-lookbook.png (cut into /public/lookbook/*).
 * The cards are editorial styling only — no product names, prices or stock.
 *
 * All motion is automatic CSS (entrance, float, twinkle); nothing follows the cursor.
 */

const CHILDREN: MediaRef = {
  src: "/lookbook/lookbook-children.webp",
  alt: "A smiling girl in a blush floral tulle dress beside a boy in a soft-blue blazer and bow tie",
  width: 500,
  height: 941,
};

interface Look {
  key: "dress" | "outfit" | "shoes" | "hat";
  width: number;
  height: number;
  badge: LucideIcon;
  gold?: boolean;
  swatches: string[];
}

const LOOKS: Look[] = [
  { key: "dress", width: 140, height: 178, badge: Gift, swatches: ["var(--tk-blush-deep)", "var(--tk-coral)", "var(--tk-gold-soft)"] },
  { key: "shoes", width: 106, height: 94, badge: Crown, swatches: ["var(--tk-blush-deep)", "var(--tk-ivory-deep)", "var(--tk-blush)"] },
  { key: "outfit", width: 144, height: 180, badge: Star, gold: true, swatches: ["var(--tk-sky)", "var(--tk-navy-soft)", "var(--tk-gold)"] },
  { key: "hat", width: 132, height: 122, badge: ShoppingBag, swatches: ["var(--tk-blush)", "var(--tk-gold)", "var(--tk-gold-soft)"] },
];

// Only some motifs move: a few stars twinkle, a few hearts pulse, the rest stay still.
const DECOR = [
  { kind: "star", size: 22, className: styles.decorA, effect: styles.twinkle },
  { kind: "heart", size: 16, className: styles.decorB, effect: styles.pulse },
  { kind: "star", size: 14, className: styles.decorC },
  { kind: "heart", size: 13, className: styles.decorD },
  { kind: "star", size: 18, className: styles.decorE, effect: styles.twinkle },
  { kind: "heart", size: 18, className: styles.decorF, effect: styles.pulse },
] as const;

const SPARKLES = [styles.sparkleA, styles.sparkleB, styles.sparkleC];

export function FloatingLookbook({ image, mobileImage }: { image: MediaRef | null; mobileImage: MediaRef | null }) {
  // A photo configured in the CMS replaces the bundled art inside the arch.
  const main = image ?? CHILDREN;
  const mobile = mobileImage && mobileImage !== main ? mobileImage : null;

  return (
    <div className={styles.stage}>
      <span className={styles.halo} aria-hidden="true" />
      <span className={styles.cloudA} aria-hidden="true" />
      <span className={styles.cloudB} aria-hidden="true" />

      <div className={styles.arch}>
        <div className={styles.archEnter}>
          <span className={styles.glow} aria-hidden="true" />
          <div className={styles.archFloat}>
            <div className={styles.archFrame}>
              <Image
                src={main.src}
                alt={main.alt}
                fill
                loading="eager"
                fetchPriority="high"
                sizes="(min-width: 960px) 320px, 50vw"
                className={`${styles.archImage} ${mobile ? styles.desktopOnly : ""}`}
                style={{ objectPosition: main.focal ?? "50% 0%" }}
              />
              {mobile && (
                <Image
                  src={mobile.src}
                  alt={mobile.alt}
                  fill
                  sizes="50vw"
                  fetchPriority="high"
                  className={`${styles.archImage} ${styles.mobileOnly}`}
                  style={{ objectPosition: mobile.focal ?? "50% 0%" }}
                />
              )}
            </div>
          </div>
        </div>
      </div>

      <div className={styles.looks} aria-hidden="true">
        {LOOKS.map(({ key, width, height, badge: Badge, gold, swatches }) => (
          <div key={key} className={`${styles.slot} ${styles[key]}`}>
            <span className={styles.cardShadow} />
            <div className={styles.float}>
              <div className={styles.card}>
                <div className={styles.photo} style={{ "--ratio": `${width} / ${height}` } as CSSProperties}>
                  <Image src={`/lookbook/lookbook-${key}.webp`} alt="" fill sizes="160px" className={styles.photoImage} />
                  <span className={styles.like}>
                    <Heart />
                  </span>
                </div>
                <span className={styles.swatches}>
                  {swatches.map((colour) => (
                    <i key={colour} style={{ background: colour }} />
                  ))}
                </span>
                <span className={`${styles.badge} ${gold ? styles.badgeGold : ""}`}>
                  <Badge />
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {DECOR.map(({ kind, size, className, ...rest }, i) => (
        <span key={i} className={`${styles.decor} ${className}`} aria-hidden="true">
          <Motif kind={kind} size={size} className={"effect" in rest ? rest.effect : undefined} />
        </span>
      ))}
      {SPARKLES.map((className) => (
        <span key={className} className={`${styles.sparkle} ${className}`} aria-hidden="true">
          <Motif kind="star" size={10} />
        </span>
      ))}
    </div>
  );
}
