import type { CSSProperties } from "react";

import styles from "./Motif.module.css";

type MotifKind = "star" | "heart" | "dot";

interface MotifProps {
  kind?: MotifKind;
  size?: number;
  color?: string;
  className?: string;
  style?: CSSProperties;
  twinkle?: boolean;
}

/** Small decorative brand motif (always aria-hidden). */
export function Motif({ kind = "star", size = 16, color, className, style, twinkle = false }: MotifProps) {
  const common = {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    "aria-hidden": true,
    focusable: false,
    className: [styles.motif, twinkle && styles.twinkle, className].filter(Boolean).join(" "),
    style: { color, ...style },
  } as const;

  if (kind === "heart") {
    return (
      <svg {...common}>
        <path
          fill="currentColor"
          d="M12 21s-7.5-4.6-9.6-9.2C.9 8.4 2.9 4.5 6.6 4.5c2.2 0 3.6 1.2 4.4 2.5.8-1.3 2.2-2.5 4.4-2.5 3.7 0 5.7 3.9 4.2 7.3C19.5 16.4 12 21 12 21Z"
        />
      </svg>
    );
  }
  if (kind === "dot") {
    return (
      <svg {...common}>
        <circle cx="12" cy="12" r="6" fill="currentColor" />
      </svg>
    );
  }
  return (
    <svg {...common}>
      <path
        fill="currentColor"
        d="M12 1.5c.6 4.8 2.9 8.6 10.5 10.5-7.6 1.9-9.9 5.7-10.5 10.5-.6-4.8-2.9-8.6-10.5-10.5C9.1 10.1 11.4 6.3 12 1.5Z"
      />
    </svg>
  );
}
