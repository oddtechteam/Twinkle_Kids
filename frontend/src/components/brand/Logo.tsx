import Image from "next/image";
import Link from "next/link";

import { isRenderableImage } from "@/lib/catalog/adapters";
import type { MediaRef } from "@/lib/content/types";

import styles from "./Logo.module.css";

interface LogoProps {
  tone?: "dark" | "light";
  size?: "md" | "lg";
  /** Brand name from site settings (CMS); defaults to the registered brand name. */
  name?: string;
  /** Uploaded logo from store settings; the drawn wordmark is used when absent. */
  image?: MediaRef | null;
}

/** Wordmark: a twinkling star + "Twinkle Kids" set in the rounded heading face. */
export function Logo({ tone = "dark", size = "md", name = "Twinkle Kids", image }: LogoProps) {
  if (image && isRenderableImage(image.src)) {
    const height = size === "lg" ? 52 : 40;
    const width = Math.round((image.width / Math.max(image.height, 1)) * height);
    return (
      <Link href="/" className={styles.logo} aria-label={`${name} — home`}>
        <Image src={image.src} alt="" width={width} height={height} priority className={styles.image} />
      </Link>
    );
  }
  const [first, ...rest] = name.split(" ");
  return (
    <Link href="/" className={`${styles.logo} ${styles[tone]} ${styles[size]}`} aria-label={`${name} — home`}>
      <svg viewBox="0 0 32 32" className={styles.mark} aria-hidden="true" focusable="false">
        <circle cx="16" cy="16" r="15" className={styles.markBg} />
        <path
          className={styles.markStar}
          d="M16 5.5c.8 5.4 3.4 8.2 10 10.5-6.6 2.3-9.2 5.1-10 10.5-.8-5.4-3.4-8.2-10-10.5 6.6-2.3 9.2-5.1 10-10.5Z"
        />
        <circle cx="24.5" cy="8" r="1.6" className={styles.markDot} />
      </svg>
      <span className={styles.word}>
        <span>{first}</span>
        {rest.length > 0 && <span className={styles.accentWord}>{rest.join(" ")}</span>}
      </span>
    </Link>
  );
}
