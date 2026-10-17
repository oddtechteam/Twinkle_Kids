import type { Money } from "@/lib/api/types";

const whole = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});
const exact = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/** Display-only formatting of an API decimal string: "399.00" -> "₹399", "399.50" -> "₹399.50". */
export function formatMoney(value: Money): string {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return value;
  return Number.isInteger(amount) ? whole.format(amount) : exact.format(amount);
}

export function titleFromSlug(slug: string): string {
  return slug
    .split("-")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

/** "1 product" / "12 products". */
export function plural(count: number, one: string, many = `${one}s`): string {
  return `${count} ${count === 1 ? one : many}`;
}

const dateTime = new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" });

/** "17 Oct 2026, 3:45 pm" from an ISO timestamp. */
export function formatDateTime(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : dateTime.format(date);
}
