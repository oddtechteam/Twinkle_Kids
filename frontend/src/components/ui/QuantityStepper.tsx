"use client";

import { Minus, Plus } from "lucide-react";

import styles from "./QuantityStepper.module.css";

interface QuantityStepperProps {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  /** Accessible name, e.g. "Quantity" or "Quantity for Party Dress". */
  label?: string;
  disabled?: boolean;
  size?: "sm" | "md";
}

/** − / value / + control. The buttons are real buttons; the value is announced politely. */
export function QuantityStepper({
  value,
  onChange,
  min = 1,
  max = 99,
  label = "Quantity",
  disabled = false,
  size = "md",
}: QuantityStepperProps) {
  const upper = Math.max(min, max);
  return (
    <div className={`${styles.stepper} ${styles[size]}`} role="group" aria-label={label}>
      <button
        type="button"
        className={styles.button}
        onClick={() => onChange(Math.max(min, value - 1))}
        disabled={disabled || value <= min}
        aria-label={`Decrease ${label.toLowerCase()}`}
      >
        <Minus aria-hidden="true" size={16} strokeWidth={2.4} />
      </button>
      <output className={styles.value} aria-live="polite" aria-label={`${label}: ${value}`}>
        {value}
      </output>
      <button
        type="button"
        className={styles.button}
        onClick={() => onChange(Math.min(upper, value + 1))}
        disabled={disabled || value >= upper}
        aria-label={`Increase ${label.toLowerCase()}`}
      >
        <Plus aria-hidden="true" size={16} strokeWidth={2.4} />
      </button>
    </div>
  );
}
