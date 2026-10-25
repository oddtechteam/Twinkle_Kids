import styles from "./Loader.module.css";

interface LoaderProps {
  /** Visible status text. */
  label?: string;
  /** "page": centred in the content area (never full-screen). "inline": compact, for panels. */
  variant?: "page" | "inline";
  className?: string;
}

/**
 * Twinkle Kids loader: a little dress swinging on a hanger, with soft sparkles.
 *
 * Render it only while something is genuinely loading. It fades in after a short delay (CSS),
 * so fast loads never flash it, and it is a polite live region for assistive tech. Motion
 * stops under prefers-reduced-motion; the status text always remains.
 */
export function Loader({ label = "Getting little styles ready…", variant = "page", className }: LoaderProps) {
  return (
    <div className={`${styles.loader} ${styles[variant]} ${className ?? ""}`} role="status" aria-live="polite">
      <svg className={styles.art} viewBox="0 0 120 120" aria-hidden="true" focusable="false">
        {/* soft halo */}
        <circle cx="60" cy="64" r="44" className={styles.halo} />
        {/* sparkles */}
        <path className={`${styles.sparkle} ${styles.sparkleA}`} d="M22 34c.6 4 2.4 6 6.5 6.6-4.1.6-5.9 2.6-6.5 6.6-.6-4-2.4-6-6.5-6.6 4.1-.6 5.9-2.6 6.5-6.6Z" />
        <path className={`${styles.sparkle} ${styles.sparkleB}`} d="M98 26c.5 3.2 1.9 4.8 5.2 5.3-3.3.5-4.7 2.1-5.2 5.3-.5-3.2-1.9-4.8-5.2-5.3 3.3-.5 4.7-2.1 5.2-5.3Z" />
        <path className={`${styles.sparkle} ${styles.sparkleC}`} d="M100 82c.4 2.6 1.5 3.9 4.2 4.3-2.7.4-3.8 1.7-4.2 4.3-.4-2.6-1.5-3.9-4.2-4.3 2.7-.4 3.8-1.7 4.2-4.3Z" />
        {/* hook (fixed) */}
        <path className={styles.hook} d="M60 30v-6a6 6 0 1 0-6-6" />
        {/* hanger + dress swing together from the hook */}
        <g className={styles.swing}>
          <path className={styles.hanger} d="M60 30 30 48h60Z" />
          <path
            className={styles.dress}
            d="M50 48c0 4 4.5 7 10 7s10-3 10-7l6 6-4 7-3-2 9 30c-6 3-12 4-18 4s-12-1-18-4l9-30-3 2-4-7Z"
          />
          <path className={styles.sash} d="M48.5 66h23" />
          <circle className={styles.bow} cx="60" cy="66" r="2.6" />
        </g>
      </svg>
      <p className={styles.label}>{label}</p>
      <span className={styles.track} aria-hidden="true">
        <span className={styles.bar} />
      </span>
    </div>
  );
}
