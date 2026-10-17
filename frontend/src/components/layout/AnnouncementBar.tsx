import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { Motif } from "@/components/ui/Motif";
import type { Announcement } from "@/lib/content/types";
import styles from "./AnnouncementBar.module.css";

export function AnnouncementBar({ announcement }: { announcement: Announcement }) {
  if (!announcement.visible || !announcement.message) return null;
  return (
    <aside className={styles.bar} aria-label="Announcement">
      <div className={`container ${styles.inner}`}>
        <Motif size={12} twinkle className={styles.star} />
        <p className={styles.message}>
          {announcement.message}
          {announcement.link && (
            <Link href={announcement.link.href} className={styles.link}>
              {announcement.link.label}
              <ArrowRight aria-hidden="true" size={14} strokeWidth={2.25} />
            </Link>
          )}
        </p>
        <Motif size={12} twinkle className={styles.star} style={{ animationDelay: "1.2s" }} />
      </div>
    </aside>
  );
}
