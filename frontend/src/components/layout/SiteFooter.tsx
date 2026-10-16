import { Logo } from "@/components/brand/Logo";
import { siteFallback } from "@/config/site";
import styles from "./SiteFooter.module.css";

export function SiteFooter() {
  return (
    <footer className={styles.footer}>
      <div className={`container ${styles.inner}`}>
        <div className={styles.brand}>
          <Logo tone="light" />
          <p className={styles.tagline}>{siteFallback.tagline}</p>
        </div>
        {/* Footer links, contact details and social profiles come from Site Settings (Phase 5). */}
        <p className={styles.copy}>© {siteFallback.name}. All rights reserved.</p>
      </div>
    </footer>
  );
}
