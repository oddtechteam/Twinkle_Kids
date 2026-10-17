import { ChevronDown } from "lucide-react";
import type { ComponentProps, CSSProperties, ReactNode } from "react";

import styles from "./Form.module.css";

/** Size/filter chip backed by a real checkbox or radio input (keyboard + screen reader native). */
export function ChoiceChip({
  label,
  type = "checkbox",
  unavailable = false,
  className,
  ...input
}: { label: ReactNode; type?: "checkbox" | "radio"; unavailable?: boolean } & Omit<
  ComponentProps<"input">,
  "type"
>) {
  return (
    <label className={`${styles.chip} ${unavailable ? styles.unavailable : ""} ${className ?? ""}`}>
      <input type={type} className={styles.chipInput} {...input} />
      <span className={styles.chipFace}>{label}</span>
    </label>
  );
}

/** Colour swatch backed by a real input; the colour name is always available to assistive tech. */
export function ColourSwatch({
  colourName,
  hex,
  type = "radio",
  unavailable = false,
  showLabel = false,
  ...input
}: {
  colourName: string;
  hex: string | null;
  type?: "checkbox" | "radio";
  unavailable?: boolean;
  showLabel?: boolean;
} & Omit<ComponentProps<"input">, "type">) {
  const style = { "--swatch": hex ?? "var(--tk-navy-mist)" } as CSSProperties;
  return (
    <label className={`${styles.swatch} ${unavailable ? styles.unavailable : ""}`} title={colourName}>
      <input type={type} className={styles.chipInput} aria-label={colourName} {...input} />
      <span className={styles.swatchDot} style={style} aria-hidden="true" />
      {showLabel && <span className={styles.swatchLabel}>{colourName}</span>}
    </label>
  );
}

export function Select({
  label,
  hideLabel = false,
  children,
  className,
  ...select
}: { label: string; hideLabel?: boolean } & ComponentProps<"select">) {
  return (
    <label className={`${styles.field} ${className ?? ""}`}>
      <span className={hideLabel ? "visually-hidden" : styles.label}>{label}</span>
      <span className={styles.selectWrap}>
        <select className={styles.select} {...select}>
          {children}
        </select>
        <ChevronDown aria-hidden="true" size={18} className={styles.chevron} />
      </span>
    </label>
  );
}

export function TextField({
  label,
  hideLabel = false,
  icon,
  className,
  ...input
}: { label: string; hideLabel?: boolean; icon?: ReactNode } & ComponentProps<"input">) {
  return (
    <label className={`${styles.field} ${className ?? ""}`}>
      <span className={hideLabel ? "visually-hidden" : styles.label}>{label}</span>
      <span className={styles.inputWrap}>
        {icon && <span className={styles.inputIcon}>{icon}</span>}
        <input className={`${styles.input} ${icon ? styles.withIcon : ""}`} {...input} />
      </span>
    </label>
  );
}

export function Accordion({
  title,
  children,
  defaultOpen = false,
}: {
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  return (
    <details className={styles.accordion} open={defaultOpen}>
      <summary className={styles.summary}>
        <span>{title}</span>
        <ChevronDown aria-hidden="true" size={20} className={styles.summaryIcon} />
      </summary>
      <div className={styles.accordionBody}>{children}</div>
    </details>
  );
}
