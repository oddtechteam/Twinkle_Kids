import { Skeleton } from "@/components/ui/Feedback";
import styles from "./ProductSkeleton.module.css";

/** Product page placeholder with the real layout's proportions (no jump when it swaps in). */
export function ProductSkeleton() {
  return (
    <div className={`container ${styles.page}`} aria-busy="true" aria-label="Loading product">
      <Skeleton width="14rem" height="0.9rem" />
      <div className={styles.layout}>
        <Skeleton height="auto" radius="var(--radius-xl)" className={styles.image} />
        <div className={styles.info}>
          <Skeleton width="70%" height="2.5rem" radius="var(--radius-pill)" />
          <Skeleton width="35%" height="1.75rem" radius="var(--radius-pill)" />
          <Skeleton height="6rem" radius="var(--radius-lg)" />
          <Skeleton height="3.25rem" radius="var(--radius-pill)" />
        </div>
      </div>
    </div>
  );
}
