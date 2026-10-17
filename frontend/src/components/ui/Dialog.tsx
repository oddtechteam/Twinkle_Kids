"use client";

import { X } from "lucide-react";
import { type ReactNode, useEffect, useId, useRef } from "react";

import styles from "./Dialog.module.css";

export type DialogVariant = "modal" | "drawer-start" | "drawer-end" | "top";

interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  hideTitle?: boolean;
  description?: string;
  variant?: DialogVariant;
  children: ReactNode;
  footer?: ReactNode;
  className?: string;
}

/**
 * Accessible modal built on the native <dialog> element: real modality, focus containment,
 * Esc to close, focus restoration and a backdrop — no focus-trap library needed.
 */
export function Dialog({
  open,
  onClose,
  title,
  hideTitle = false,
  description,
  variant = "modal",
  children,
  footer,
  className,
}: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const descriptionId = useId();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      className={`${styles.dialog} ${styles[variant]} ${className ?? ""}`}
      aria-labelledby={titleId}
      aria-describedby={description ? descriptionId : undefined}
      onClose={onClose}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === ref.current) onClose(); // backdrop click
      }}
    >
      <div className={styles.panel}>
        <header className={`${styles.header} ${hideTitle ? styles.headerBare : ""}`}>
          <h2 id={titleId} className={hideTitle ? "visually-hidden" : styles.title}>
            {title}
          </h2>
          <button type="button" className={styles.close} onClick={onClose} aria-label="Close">
            <X aria-hidden="true" size={22} strokeWidth={1.75} />
          </button>
        </header>
        {description && (
          <p id={descriptionId} className={styles.description}>
            {description}
          </p>
        )}
        <div className={styles.body}>{children}</div>
        {footer && <footer className={styles.footer}>{footer}</footer>}
      </div>
    </dialog>
  );
}
