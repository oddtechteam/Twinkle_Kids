import Link from "next/link";
import { Sparkle } from "lucide-react";

import { siteFallback } from "@/config/site";
import styles from "./Logo.module.css";

interface LogoProps {
  tone?: "dark" | "light";
}

export function Logo({ tone = "dark" }: LogoProps) {
  return (
    <Link
      href="/"
      className={`${styles.logo} ${styles[tone]}`}
      aria-label={`${siteFallback.name} home`}
    >
      <Sparkle className={styles.star} aria-hidden="true" strokeWidth={1.75} />
      <span className={styles.word}>
        Twinkle<span className={styles.kids}>Kids</span>
      </span>
    </Link>
  );
}
