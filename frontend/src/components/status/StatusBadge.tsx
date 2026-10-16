import { CircleAlert, CircleCheck } from "lucide-react";

import styles from "./StatusBadge.module.css";

interface StatusBadgeProps {
  ok: boolean;
  label?: string;
}

export function StatusBadge({ ok, label }: StatusBadgeProps) {
  const Icon = ok ? CircleCheck : CircleAlert;
  return (
    <span className={`${styles.badge} ${ok ? styles.ok : styles.down}`}>
      <Icon aria-hidden="true" size={16} strokeWidth={2.25} />
      {label ?? (ok ? "Operational" : "Unavailable")}
    </span>
  );
}
