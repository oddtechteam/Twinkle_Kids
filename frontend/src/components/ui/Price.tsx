import type { Money, Price as PriceData } from "@/lib/api/types";
import { formatMoney } from "@/lib/format";

import styles from "./Price.module.css";

interface PriceProps {
  price: PriceData;
  /** Lowest variant price; shown as "From …" when prices vary by option. */
  fromPrice?: Money;
  priceVaries?: boolean;
  size?: "sm" | "md" | "lg";
  showBadge?: boolean;
}

/**
 * Selling price, crossed-out MRP and discount badge — all straight from the API's PriceView.
 * Nothing is recalculated here; a comparison is shown only when the backend reports a discount.
 */
export function Price({ price, fromPrice, priceVaries = false, size = "md", showBadge = true }: PriceProps) {
  const hasDiscount = price.discount_amount !== null && price.original_price !== null;
  // When variants price differently, only claim a comparison if the base price is the "from" price.
  const showFrom = priceVaries && fromPrice !== undefined;
  const selling = showFrom ? fromPrice : price.selling_price;
  const comparable = hasDiscount && (!showFrom || fromPrice === price.selling_price);

  const spoken = [
    showFrom ? `From ${formatMoney(selling)}` : `Price ${formatMoney(selling)}`,
    comparable && price.original_price ? `, was ${formatMoney(price.original_price)}` : "",
    comparable && price.discount_percent ? `, ${price.discount_percent}% off` : "",
  ].join("");

  return (
    <p className={`${styles.price} ${styles[size]}`}>
      <span className="visually-hidden">{spoken}</span>
      <span aria-hidden="true" className={styles.row}>
        {showFrom && <span className={styles.from}>From</span>}
        <span className={styles.selling}>{formatMoney(selling)}</span>
        {comparable && price.original_price && (
          <s className={styles.compare}>{formatMoney(price.original_price)}</s>
        )}
        {comparable && showBadge && price.discount_percent !== null && price.discount_percent > 0 && (
          <span className={styles.badge}>{price.discount_percent}% off</span>
        )}
      </span>
    </p>
  );
}
