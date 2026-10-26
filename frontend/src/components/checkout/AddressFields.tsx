"use client";

import { useId } from "react";

import type { PostalAddress } from "@/lib/api/types";
import styles from "./CheckoutView.module.css";

export const EMPTY_ADDRESS: PostalAddress = {
  full_name: "",
  phone: "",
  line1: "",
  line2: "",
  landmark: "",
  city: "",
  state: "",
  postal_code: "",
};

const PIN = /^[1-9][0-9]{5}$/;
const PHONE = /^\+?[0-9][0-9 -]{6,18}$/;

/** Same rules as the backend (which re-validates everything). Keys match the field names. */
export function addressErrors(address: PostalAddress): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!address.full_name.trim()) errors.full_name = "Enter the recipient's name.";
  if (!PHONE.test(address.phone.trim()) || address.phone.replace(/\D/g, "").length < 8) {
    errors.address_phone = "Enter a valid mobile number for delivery.";
  }
  if (!address.line1.trim()) errors.line1 = "Enter the house number and street.";
  if (!address.city.trim()) errors.city = "Enter the city.";
  if (!address.state.trim()) errors.state = "Enter the state.";
  if (!PIN.test(address.postal_code.replace(/\s/g, ""))) errors.postal_code = "Enter a valid 6-digit PIN code.";
  return errors;
}

const FIELDS: {
  key: keyof PostalAddress;
  errorKey?: string;
  label: string;
  autoComplete: string;
  required?: boolean;
  wide?: boolean;
  maxLength: number;
  inputMode?: "tel" | "numeric";
}[] = [
  { key: "full_name", label: "Recipient name", autoComplete: "shipping name", required: true, maxLength: 120 },
  { key: "phone", errorKey: "address_phone", label: "Delivery phone", autoComplete: "shipping tel", required: true, maxLength: 20, inputMode: "tel" },
  { key: "line1", label: "House no., building, street", autoComplete: "shipping address-line1", required: true, wide: true, maxLength: 200 },
  { key: "line2", label: "Area, locality (optional)", autoComplete: "shipping address-line2", wide: true, maxLength: 200 },
  { key: "landmark", label: "Landmark (optional)", autoComplete: "off", maxLength: 120 },
  { key: "city", label: "City", autoComplete: "shipping address-level2", required: true, maxLength: 100 },
  { key: "state", label: "State", autoComplete: "shipping address-level1", required: true, maxLength: 100 },
  { key: "postal_code", label: "PIN code", autoComplete: "shipping postal-code", required: true, maxLength: 6, inputMode: "numeric" },
];

export function AddressFields({
  value,
  onChange,
  errors = {},
}: {
  value: PostalAddress;
  onChange: (next: PostalAddress) => void;
  errors?: Record<string, string>;
}) {
  const base = useId();
  return (
    <div className={styles.grid}>
      {FIELDS.map((field) => {
        const id = `${base}-${field.key}`;
        const error = errors[field.errorKey ?? field.key];
        return (
          <div key={field.key} className={`${styles.field} ${field.wide ? styles.wide : ""}`}>
            <label htmlFor={id} className={styles.label}>
              {field.label}
              {field.required && <span aria-hidden="true"> *</span>}
            </label>
            <input
              id={id}
              className={`${styles.input} ${error ? styles.invalid : ""}`}
              value={value[field.key] ?? ""}
              onChange={(e) => onChange({ ...value, [field.key]: e.target.value })}
              autoComplete={field.autoComplete}
              inputMode={field.inputMode}
              maxLength={field.maxLength}
              required={field.required}
              aria-invalid={error ? true : undefined}
              aria-describedby={error ? `${id}-error` : undefined}
            />
            {error && (
              <p id={`${id}-error`} className={styles.fieldError}>
                {error}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}
