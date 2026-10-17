import Link from "next/link";
import { ArrowRight } from "lucide-react";

import type { LinkItem } from "@/lib/content/types";
import { Motif } from "./Motif";
import styles from "./SectionHeading.module.css";

interface SectionHeadingProps {
  id?: string;
  eyebrow?: string;
  title: string;
  subtitle?: string;
  link?: LinkItem;
  align?: "start" | "center";
  tone?: "default" | "inverse";
}

export function SectionHeading({
  id,
  eyebrow,
  title,
  subtitle,
  link,
  align = "start",
  tone = "default",
}: SectionHeadingProps) {
  return (
    <div className={`${styles.heading} ${styles[align]} ${styles[tone]}`}>
      <div className={styles.text}>
        {eyebrow && (
          <p className={styles.eyebrow}>
            <Motif size={12} />
            {eyebrow}
          </p>
        )}
        <h2 id={id} className={styles.title}>
          {title}
        </h2>
        {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
      </div>
      {link && (
        <Link href={link.href} className={styles.link}>
          {link.label}
          <ArrowRight aria-hidden="true" size={18} strokeWidth={2} />
        </Link>
      )}
    </div>
  );
}
