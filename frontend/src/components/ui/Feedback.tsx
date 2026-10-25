import type { CSSProperties, ReactNode } from "react";

import { Motif } from "./Motif";
import styles from "./Feedback.module.css";

export function Skeleton({
  width,
  height,
  radius,
  className,
}: {
  width?: string;
  height?: string;
  radius?: string;
  className?: string;
}) {
  const style: CSSProperties = { width, height, borderRadius: radius };
  return <span aria-hidden="true" className={`${styles.skeleton} ${className ?? ""}`} style={style} />;
}

export function EmptyState({
  title,
  description,
  action,
  icon,
  tone = "default",
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  icon?: ReactNode;
  tone?: "default" | "error";
}) {
  return (
    <div className={`${styles.empty} ${tone === "error" ? styles.error : ""}`} role={tone === "error" ? "alert" : "status"}>
      <div className={styles.emblem} aria-hidden="true">
        {icon ?? <Motif kind={tone === "error" ? "dot" : "star"} size={26} />}
        <Motif kind="star" size={10} className={styles.sparkA} />
        <Motif kind="heart" size={10} className={styles.sparkB} />
      </div>
      <h2 className={styles.title}>{title}</h2>
      {description && <p className={styles.description}>{description}</p>}
      {action && <div className={styles.action}>{action}</div>}
    </div>
  );
}

/** Text page placeholder (CMS pages, about, contact): title + paragraph lines, no layout jump. */
export function ContentSkeleton() {
  return (
    <div className={`container-narrow ${styles.contentSkeleton}`} aria-busy="true" aria-label="Loading page">
      <Skeleton width="9rem" height="0.9rem" />
      <Skeleton width="min(24rem, 75%)" height="2.75rem" radius="var(--radius-pill)" />
      {["100%", "96%", "88%", "100%", "64%"].map((width, index) => (
        <Skeleton key={index} width={width} height="1rem" />
      ))}
    </div>
  );
}
