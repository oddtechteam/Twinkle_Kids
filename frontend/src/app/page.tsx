import Link from "next/link";
import { Activity } from "lucide-react";

import { siteFallback } from "@/config/site";
import styles from "./page.module.css";

/*
 * Foundation placeholder. In Phase 5 this page renders admin-managed homepage
 * sections (hero banners, featured collections, product rails) from the CMS API.
 */
export default function HomePage() {
  return (
    <section className={styles.hero} aria-labelledby="hero-title">
      <div className={styles.sky} aria-hidden="true">
        {Array.from({ length: 7 }, (_, i) => (
          <span key={i} className={styles.twinkle} />
        ))}
      </div>

      <div className={`container ${styles.content}`}>
        <p className={styles.eyebrow}>Children&apos;s fashion boutique</p>
        <h1 id="hero-title" className={styles.title}>
          {siteFallback.tagline.replace(/\.$/, "")}
        </h1>
        <p className={styles.lede}>
          Our new boutique is being stitched together with care. Soft fabrics, sweet details and
          outfits made for play — arriving soon.
        </p>

        {process.env.NODE_ENV !== "production" && (
          <Link href="/status" className={styles.devLink}>
            <Activity aria-hidden="true" size={18} strokeWidth={2} />
            View system status
          </Link>
        )}
      </div>
    </section>
  );
}
