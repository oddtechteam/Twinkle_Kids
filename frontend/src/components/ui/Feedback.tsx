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
