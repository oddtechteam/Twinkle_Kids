"use client";

/** Admin building blocks: page header, cards, fields, table, pills, confirm dialog, states. */

import Link from "next/link";
import { AlertTriangle, ArrowDown, ArrowUp, GripVertical, X } from "lucide-react";
import {
  type ComponentProps,
  type ReactNode,
  useId,
  useState,
} from "react";

import { type Crumb, Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Loader } from "@/components/ui/Loader";
import styles from "./admin.module.css";

export { styles as adminStyles };

// --- Page & layout ----------------------------------------------------------------------------

export function AdminPage({
  title,
  description,
  breadcrumbs = [],
  actions,
  children,
}: {
  title: string;
  description?: string;
  breadcrumbs?: Crumb[];
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <>
      <header className={styles.pageHeader}>
        <div>
          {breadcrumbs.length > 0 && <Breadcrumbs items={[{ label: "Admin", href: "/admin" }, ...breadcrumbs]} />}
          <h1 className={styles.pageTitle}>{title}</h1>
          {description && <p className={styles.pageDescription}>{description}</p>}
        </div>
        {actions && <div className={styles.actions}>{actions}</div>}
      </header>
      {children}
    </>
  );
}

export function Card({
  title,
  hint,
  actions,
  children,
}: {
  title?: string;
  hint?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className={styles.card}>
      {(title || actions) && (
        <div className={styles.cardHeader}>
          <div>
            {title && <h2 className={styles.cardTitle}>{title}</h2>}
            {hint && <p className={styles.cardHint}>{hint}</p>}
          </div>
          {actions && <div className={styles.actions}>{actions}</div>}
        </div>
      )}
      {children}
    </section>
  );
}

// --- Fields -----------------------------------------------------------------------------------

export function Field({
  label,
  hint,
  error,
  required,
  children,
}: {
  label: string;
  hint?: string;
  error?: string | null;
  required?: boolean;
  children: (id: string) => ReactNode;
}) {
  const id = useId();
  return (
    <div className={styles.field}>
      <label htmlFor={id} className={styles.label}>
        {label} {required && <span className={styles.required}>*</span>}
      </label>
      {children(id)}
      {error ? <p className={styles.errorText}>{error}</p> : hint && <p className={styles.hint}>{hint}</p>}
    </div>
  );
}

export function TextInput({
  label,
  hint,
  error,
  required,
  value,
  onChange,
  ...rest
}: {
  label: string;
  hint?: string;
  error?: string | null;
  value: string;
  onChange: (value: string) => void;
} & Omit<ComponentProps<"input">, "value" | "onChange">) {
  return (
    <Field label={label} hint={hint} error={error} required={required}>
      {(id) => (
        <input
          id={id}
          className={styles.input}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          aria-invalid={error ? true : undefined}
          required={required}
          {...rest}
        />
      )}
    </Field>
  );
}

export function TextArea({
  label,
  hint,
  value,
  onChange,
  rows = 4,
  ...rest
}: {
  label: string;
  hint?: string;
  value: string;
  onChange: (value: string) => void;
  rows?: number;
} & Omit<ComponentProps<"textarea">, "value" | "onChange">) {
  return (
    <Field label={label} hint={hint}>
      {(id) => (
        <textarea
          id={id}
          className={styles.textarea}
          value={value}
          rows={rows}
          onChange={(e) => onChange(e.target.value)}
          {...rest}
        />
      )}
    </Field>
  );
}

export function SelectInput({
  label,
  hint,
  value,
  onChange,
  options,
  placeholder,
}: {
  label: string;
  hint?: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  placeholder?: string;
}) {
  return (
    <Field label={label} hint={hint}>
      {(id) => (
        <select id={id} className={styles.select} value={value} onChange={(e) => onChange(e.target.value)}>
          {placeholder !== undefined && <option value="">{placeholder}</option>}
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      )}
    </Field>
  );
}

/** Money input (₹). Keeps the exact decimal string; validated as ≤ 2 decimal places. */
export function MoneyInput({
  label,
  hint,
  value,
  onChange,
  required,
  placeholder,
}: {
  label: string;
  hint?: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  placeholder?: string;
}) {
  const valid = value === "" || /^\d{1,10}(\.\d{1,2})?$/.test(value);
  return (
    <Field label={label} hint={hint} error={valid ? null : "Use a number with up to 2 decimals"} required={required}>
      {(id) => (
        <div className={styles.prefixed}>
          <span className={styles.prefix} aria-hidden="true">
            ₹
          </span>
          <input
            id={id}
            className={styles.input}
            inputMode="decimal"
            value={value}
            placeholder={placeholder}
            aria-invalid={valid ? undefined : true}
            onChange={(e) => onChange(e.target.value.trim())}
            required={required}
          />
        </div>
      )}
    </Field>
  );
}

export function Toggle({
  label,
  checked,
  onChange,
  disabled,
}: {
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <label className={styles.toggle}>
      <input
        type="checkbox"
        role="switch"
        className={styles.toggleInput}
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
      {label}
    </label>
  );
}

/** Multi-select as a checkbox list (categories, collections). */
export function CheckList({
  label,
  options,
  selected,
  onChange,
  empty = "Nothing to choose yet.",
}: {
  label: string;
  options: { value: string; label: string }[];
  selected: string[];
  onChange: (value: string[]) => void;
  empty?: string;
}) {
  return (
    <fieldset className={styles.field} style={{ border: 0, padding: 0, margin: 0 }}>
      <legend className={styles.label}>{label}</legend>
      <div className={styles.checkList}>
        {options.length === 0 && <p className={styles.hint}>{empty}</p>}
        {options.map((o) => (
          <label key={o.value} className={styles.checkItem}>
            <input
              type="checkbox"
              checked={selected.includes(o.value)}
              onChange={(e) =>
                onChange(e.target.checked ? [...selected, o.value] : selected.filter((v) => v !== o.value))
              }
            />
            {o.label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

/** Free-form tag list (badges, sizes, colours). */
export function TagInput({
  label,
  hint,
  values,
  onChange,
  max,
  maxLength = 24,
}: {
  label: string;
  hint?: string;
  values: string[];
  onChange: (value: string[]) => void;
  max?: number;
  maxLength?: number;
}) {
  const [draft, setDraft] = useState("");
  const add = () => {
    const value = draft.trim().slice(0, maxLength);
    if (!value || values.includes(value) || (max !== undefined && values.length >= max)) return;
    onChange([...values, value]);
    setDraft("");
  };
  return (
    <Field label={label} hint={hint}>
      {(id) => (
        <div className={styles.stack} style={{ gap: "var(--space-2)" }}>
          <div className={styles.chips}>
            {values.map((v) => (
              <span key={v} className={styles.chip}>
                {v}
                <button
                  type="button"
                  className={styles.chipRemove}
                  onClick={() => onChange(values.filter((x) => x !== v))}
                  aria-label={`Remove ${v}`}
                >
                  <X size={12} aria-hidden="true" />
                </button>
              </span>
            ))}
          </div>
          <div style={{ display: "flex", gap: "var(--space-2)" }}>
            <input
              id={id}
              className={styles.input}
              value={draft}
              maxLength={maxLength}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  add();
                }
              }}
              disabled={max !== undefined && values.length >= max}
            />
            <Button size="sm" variant="soft" onClick={add}>
              Add
            </Button>
          </div>
        </div>
      )}
    </Field>
  );
}

// --- Data display -----------------------------------------------------------------------------

export interface Column<T> {
  header: string;
  render: (row: T) => ReactNode;
  align?: "end";
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  empty,
}: {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  empty: ReactNode;
}) {
  if (rows.length === 0) return <div className={styles.card}>{empty}</div>;
  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.header} style={c.align === "end" ? { textAlign: "right" } : undefined}>
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)}>
              {columns.map((c) => (
                <td key={c.header} data-label={c.header} style={c.align === "end" ? { textAlign: "right" } : undefined}>
                  {c.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Pill({ tone, children }: { tone: "green" | "amber" | "grey" | "red"; children: ReactNode }) {
  const map = { green: styles.pillGreen, amber: styles.pillAmber, grey: styles.pillGrey, red: styles.pillRed };
  return <span className={`${styles.pill} ${map[tone]}`}>{children}</span>;
}

export function StatusPill({ status }: { status: string }) {
  const tone =
    status === "active" || status === "published" ? "green" : status === "archived" ? "grey" : "amber";
  return <Pill tone={tone}>{status}</Pill>;
}

/** Branded loader for admin data that is genuinely loading (fades in after a short delay). */
export function LoadingState({ label = "Getting things ready…", inline = false }: { label?: string; inline?: boolean }) {
  return <Loader label={label} variant={inline ? "inline" : "page"} />;
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className={`${styles.notice}`} role="alert" style={{ display: "flex", gap: "var(--space-3)", alignItems: "center" }}>
      <AlertTriangle size={18} aria-hidden="true" />
      <span style={{ flex: 1 }}>{message}</span>
      {onRetry && (
        <Button size="sm" variant="outline" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}

export function LinkButton({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link href={href} className={styles.menuItem} style={{ display: "inline-flex" }}>
      {children}
    </Link>
  );
}

// --- Confirm dialog ---------------------------------------------------------------------------

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Confirm",
  destructive = false,
  pending = false,
  onConfirm,
  onClose,
}: {
  open: boolean;
  title: string;
  message: ReactNode;
  confirmLabel?: string;
  destructive?: boolean;
  pending?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}) {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={title}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button variant={destructive ? "accent" : "primary"} onClick={onConfirm} loading={pending}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      <div style={{ color: "var(--color-text-muted)" }}>{message}</div>
    </Dialog>
  );
}

// --- Sortable list (drag-and-drop + keyboard/touch buttons) -----------------------------------

export function SortableList<T>({
  items,
  getId,
  onReorder,
  renderItem,
  renderActions,
  label,
}: {
  items: T[];
  getId: (item: T) => string;
  onReorder: (items: T[]) => void;
  renderItem: (item: T, index: number) => ReactNode;
  renderActions?: (item: T, index: number) => ReactNode;
  label: string;
}) {
  const [dragging, setDragging] = useState<number | null>(null);
  const [over, setOver] = useState<number | null>(null);

  const move = (from: number, to: number) => {
    if (to < 0 || to >= items.length || from === to) return;
    const next = [...items];
    const [moved] = next.splice(from, 1);
    next.splice(to, 0, moved as T);
    onReorder(next);
  };

  return (
    <ol className={styles.sortList} aria-label={label}>
      {items.map((item, index) => (
        <li
          key={getId(item)}
          className={styles.sortItem}
          draggable
          data-dragging={dragging === index}
          data-over={over === index && dragging !== index}
          onDragStart={(e) => {
            setDragging(index);
            e.dataTransfer.effectAllowed = "move";
          }}
          onDragOver={(e) => {
            e.preventDefault();
            setOver(index);
          }}
          onDragLeave={() => setOver((o) => (o === index ? null : o))}
          onDrop={(e) => {
            e.preventDefault();
            if (dragging !== null) move(dragging, index);
            setDragging(null);
            setOver(null);
          }}
          onDragEnd={() => {
            setDragging(null);
            setOver(null);
          }}
        >
          <span className={styles.handle} aria-hidden="true">
            <GripVertical size={18} />
          </span>
          <div className={styles.sortBody}>{renderItem(item, index)}</div>
          <div className={styles.sortControls}>
            {renderActions?.(item, index)}
            <button
              type="button"
              className={styles.iconButton}
              onClick={() => move(index, index - 1)}
              disabled={index === 0}
              aria-label="Move up"
            >
              <ArrowUp size={16} aria-hidden="true" />
            </button>
            <button
              type="button"
              className={styles.iconButton}
              onClick={() => move(index, index + 1)}
              disabled={index === items.length - 1}
              aria-label="Move down"
            >
              <ArrowDown size={16} aria-hidden="true" />
            </button>
          </div>
        </li>
      ))}
    </ol>
  );
}
