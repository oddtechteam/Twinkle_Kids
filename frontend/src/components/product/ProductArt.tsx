import type { ReactNode } from "react";

import styles from "./ProductArt.module.css";

/**
 * Illustrated garment shown when a product (or CMS slot) has no photograph yet.
 * Brand-coloured flat-lay art keeps the storefront polished without fake photography.
 */

export type ArtKind = "dress" | "tee" | "romper" | "skirt";
export type ArtTone = "blush" | "navy" | "gold" | "ivory" | "sky" | "sage";

const TONES: ArtTone[] = ["blush", "ivory", "gold", "sky", "navy", "sage"];
const KEYWORDS: [RegExp, ArtKind][] = [
  [/dress|frock|gown|tutu|party/i, "dress"],
  [/skirt|lehenga|tulle/i, "skirt"],
  [/romper|onesie|dungaree|jumpsuit|set|bodysuit|sleepsuit/i, "romper"],
  [/tee|t-shirt|shirt|top|kurta|polo|sweat/i, "tee"],
];

function hash(value: string): number {
  let h = 0;
  for (let i = 0; i < value.length; i++) h = (h * 31 + value.charCodeAt(i)) | 0;
  return Math.abs(h);
}

export function artFor(seed: string, name = seed): { kind: ArtKind; tone: ArtTone } {
  const kind =
    KEYWORDS.find(([pattern]) => pattern.test(name))?.[1] ??
    (["dress", "tee", "romper", "skirt"] as const)[hash(seed) % 4]!;
  return { kind, tone: TONES[hash(`${seed}:tone`) % TONES.length]! };
}

interface ProductArtProps {
  kind: ArtKind;
  tone?: ArtTone;
  label?: string;
  className?: string;
  /** Hide the hanger for compositions where the garment floats (hero, banners). */
  floating?: boolean;
}

export function ProductArt({ kind, tone = "blush", label, className, floating = false }: ProductArtProps) {
  return (
    <svg
      viewBox="0 0 240 300"
      className={`${styles.art} ${styles[tone]} ${className ?? ""}`}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      focusable="false"
      preserveAspectRatio="xMidYMid slice"
    >
      <rect width="240" height="300" className={styles.bg} />
      <circle cx="196" cy="58" r="64" className={styles.halo} />
      <circle cx="28" cy="262" r="46" className={styles.halo} />
      <g className={styles.sparkles}>
        <path d="M40 54c1 7 4 11 13 13-9 2-12 6-13 13-1-7-4-11-13-13 9-2 12-6 13-13Z" />
        <path d="M206 196c.6 4.5 2.6 7 8 8.4-5.4 1.4-7.4 3.9-8 8.4-.6-4.5-2.6-7-8-8.4 5.4-1.4 7.4-3.9 8-8.4Z" />
        <circle cx="62" cy="214" r="3" />
        <circle cx="184" cy="122" r="2.5" />
      </g>

      {!floating && (
        <g className={styles.hanger} fill="none" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round">
          <path d="M120 60c-1-9 4-15 11-15s11 8 6 13c-3 3-8 4-11 7" />
          <path d="M120 62 76 84M120 62l44 22" />
        </g>
      )}

      <g className={styles.garment}>{GARMENTS[kind]}</g>
    </svg>
  );
}

const GARMENTS: Record<ArtKind, ReactNode> = {
  dress: (
    <>
      <ellipse cx="91" cy="90" rx="13" ry="11" className={styles.light} />
      <ellipse cx="149" cy="90" rx="13" ry="11" className={styles.light} />
      <path d="M97 80h46l6 46H91z" className={styles.main} />
      <path d="M91 126h58l46 106c-48 22-102 22-150 0z" className={styles.main} />
      <path
        d="M45 232c8 9 17 9 25 1 8 9 17 9 25 1 8 9 17 9 25 1 8 9 17 9 25 1 8 9 17 9 25 1 8 9 17 9 25 1"
        className={styles.lightStroke}
        fill="none"
        strokeWidth="7"
        strokeLinecap="round"
      />
      <rect x="89" y="120" width="62" height="10" rx="5" className={styles.accent} />
      <path d="M120 125l-17-11v22zM120 125l17-11v22z" className={styles.accent} />
      <circle cx="120" cy="125" r="5" className={styles.detail} />
      <g className={styles.dots}>
        <circle cx="96" cy="166" r="3" />
        <circle cx="128" cy="160" r="3" />
        <circle cx="150" cy="188" r="3" />
        <circle cx="108" cy="198" r="3" />
        <circle cx="80" cy="206" r="3" />
        <circle cx="166" cy="214" r="3" />
        <circle cx="136" cy="214" r="3" />
      </g>
    </>
  ),
  tee: (
    <>
      <path
        d="M90 78c18 13 42 13 60 0l40 22-15 37-17-8v104c-26 9-50 9-76 0V129l-17 8-15-37z"
        className={styles.main}
      />
      <path d="M102 80c10 14 26 14 36 0" fill="none" strokeWidth="5" strokeLinecap="round" className={styles.detailStroke} />
      <path d="M57 116l17 8M183 116l-17 8" strokeWidth="5" strokeLinecap="round" className={styles.lightStroke} />
      <path
        d="M120 132c2.4 13 8 21 25 24-17 3-22.6 11-25 24-2.4-13-8-21-25-24 17-3 22.6-11 25-24Z"
        className={styles.accent}
      />
      <path d="M86 218c22 7 46 7 68 0" fill="none" strokeWidth="5" strokeLinecap="round" className={styles.lightStroke} />
    </>
  ),
  romper: (
    <>
      <path
        d="M92 80c15 12 41 12 56 0l26 18-11 27-10-6 2 66 8 54-38 4-5-34-5 34-38-4 8-54 2-66-10 6-11-27z"
        className={styles.main}
      />
      <path d="M104 82c6 10 26 10 32 0" fill="none" strokeWidth="5" strokeLinecap="round" className={styles.detailStroke} />
      <circle cx="120" cy="108" r="4" className={styles.detail} />
      <circle cx="120" cy="126" r="4" className={styles.detail} />
      <path
        d="M120 176s-14-8-17-16c-2.6-6.4 1-12 7-12 4 0 7 2.4 10 6 3-3.6 6-6 10-6 6 0 9.6 5.6 7 12-3 8-17 16-17 16Z"
        className={styles.accent}
      />
      <path d="M84 232l38 3M118 235l38-3" strokeWidth="6" strokeLinecap="round" className={styles.lightStroke} />
    </>
  ),
  skirt: (
    <>
      <rect x="80" y="96" width="80" height="20" rx="8" className={styles.accent} />
      <path d="M84 114h72l44 110c-50 20-110 20-160 0z" className={styles.main} />
      <path
        d="M104 120 90 222M120 120v108M136 120l14 102"
        fill="none"
        strokeWidth="3"
        strokeLinecap="round"
        className={styles.lightStroke}
      />
      <g className={styles.dots}>
        <circle cx="72" cy="196" r="3" />
        <circle cx="168" cy="190" r="3" />
        <circle cx="112" cy="164" r="3" />
        <circle cx="146" cy="150" r="3" />
      </g>
      <path d="M120 106l-14-9v18zM120 106l14-9v18z" className={styles.detail} />
    </>
  ),
};
