"use client";

import Link from "next/link";
import { CircleCheck, Mail, MessageCircle, Phone } from "lucide-react";
import { useEffect, useState } from "react";

import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { ButtonLink, buttonClass } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/Feedback";
import { Loader } from "@/components/ui/Loader";
import { fetchMyOrder } from "@/lib/account/api";
import type { CustomerOrder } from "@/lib/api/types";
import { recalledOrder } from "@/lib/checkout/api";
import type { ContactDetails } from "@/lib/content/types";
import { formatDateTime, formatMoney } from "@/lib/format";
import styles from "./OrderConfirmation.module.css";

type State = { status: "loading" } | { status: "missing" } | { status: "ready"; order: CustomerOrder };

const PAYMENT_LABELS: Record<string, string> = {
  cash_on_delivery: "Cash on delivery",
  upi_manual: "UPI (confirmed by the shop)",
  bank_transfer: "Bank transfer",
  other: "Arranged with the shop",
};

/**
 * Shown right after checkout. The order comes from this tab's memory (guests) or the account
 * (signed-in customers). There is deliberately no status or tracking information here.
 */
export function OrderConfirmation({
  reference,
  contact,
  storeName,
}: {
  reference: string;
  contact: ContactDetails;
  storeName: string;
}) {
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    const remembered = recalledOrder(reference);
    if (remembered) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- loads external data (API / session storage) on mount
      setState({ status: "ready", order: remembered });
      return;
    }
    fetchMyOrder(reference)
      .then((order) => setState({ status: "ready", order }))
      .catch(() => setState({ status: "missing" }));
  }, [reference]);

  const crumbs = [{ label: "Home", href: "/" }, { label: "Order received" }];
  if (state.status === "loading") return <Loader label="Loading your order…" />;
  if (state.status === "missing") {
    return (
      <div className={`container-narrow ${styles.page}`}>
        <Breadcrumbs items={crumbs} />
        <EmptyState
          title={`Order ${reference}`}
          description="We can't show this order's details here. If you placed it as a guest, check your email — or contact us with the order reference."
          action={<ButtonLink href="/contact">Contact us</ButtonLink>}
        />
      </div>
    );
  }

  const order = state.order;
  const address = order.shipping_address;
  return (
    <div className={`container-narrow ${styles.page}`}>
      <Breadcrumbs items={crumbs} />
      <header className={styles.hero}>
        <CircleCheck aria-hidden="true" size={40} className={styles.check} />
        <h1 className={styles.title}>Thank you — we&apos;ve received your order</h1>
        <p className={styles.reference}>
          Order reference <strong>{order.order_number}</strong>
        </p>
        <p className={styles.lede}>
          {storeName} will confirm availability and delivery with you shortly. No payment has been taken online
          {order.payment_method ? ` — you chose ${PAYMENT_LABELS[order.payment_method] ?? order.payment_method}` : ""}.
        </p>
        {order.payment_instructions && <p className={styles.instructions}>{order.payment_instructions}</p>}
      </header>

      <section className={styles.card} aria-labelledby="confirm-items">
        <h2 id="confirm-items" className={styles.cardTitle}>
          Items
        </h2>
        <ul className={styles.lines}>
          {order.lines.map((line, index) => (
            <li key={`${line.sku}-${index}`} className={styles.line}>
              <div>
                <p className={styles.name}>
                  {line.product_slug ? <Link href={`/products/${line.product_slug}`}>{line.product_name}</Link> : line.product_name}
                </p>
                <p className={styles.muted}>
                  {[line.size && `Size ${line.size}`, line.colour, `Qty ${line.quantity}`, `${formatMoney(line.unit_selling_price)} each`]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
              </div>
              <p className={styles.amount}>{formatMoney(line.line_total)}</p>
            </li>
          ))}
        </ul>
        <dl className={styles.totals}>
          <dt>Subtotal</dt>
          <dd>{formatMoney(order.subtotal)}</dd>
          {Number(order.discount_total) > 0 && (
            <>
              <dt>Discount{order.coupon_code ? ` (${order.coupon_code})` : ""}</dt>
              <dd>−{formatMoney(order.discount_total)}</dd>
            </>
          )}
          <dt>Delivery</dt>
          <dd>{Number(order.shipping_total) === 0 ? "Free / confirmed by the shop" : formatMoney(order.shipping_total)}</dd>
          <dt className={styles.grand}>Total</dt>
          <dd className={styles.grand}>{formatMoney(order.grand_total)}</dd>
        </dl>
      </section>

      <section className={styles.card} aria-labelledby="confirm-delivery">
        <h2 id="confirm-delivery" className={styles.cardTitle}>
          Delivery & contact
        </h2>
        <address className={styles.address}>
          {address.full_name}
          <br />
          {address.line1}
          {address.line2 ? `, ${address.line2}` : ""}
          <br />
          {address.landmark ? (
            <>
              {address.landmark}
              <br />
            </>
          ) : null}
          {address.city}, {address.state} {address.postal_code}
          <br />
          {address.phone}
        </address>
        <p className={styles.muted}>
          Confirmation details go to {order.customer_email}. Placed {formatDateTime(order.placed_at)}.
        </p>
      </section>

      <section className={styles.card} aria-labelledby="confirm-help">
        <h2 id="confirm-help" className={styles.cardTitle}>
          Questions about your order?
        </h2>
        <p className={styles.muted}>Contact us with your order reference {order.order_number} and we&apos;ll help.</p>
        <div className={styles.actions}>
          {contact.whatsapp && (
            <a
              href={`https://wa.me/${contact.whatsapp.replace(/\D/g, "")}?text=${encodeURIComponent(`Hello! I have a question about order ${order.order_number}.`)}`}
              className={buttonClass({ variant: "primary" })}
              target="_blank"
              rel="noopener noreferrer"
            >
              <MessageCircle aria-hidden="true" size={18} /> WhatsApp us
            </a>
          )}
          {contact.phone && (
            <a href={`tel:${contact.phone.replace(/[^\d+]/g, "")}`} className={buttonClass({ variant: "outline" })}>
              <Phone aria-hidden="true" size={18} /> Call us
            </a>
          )}
          {contact.email && (
            <a href={`mailto:${contact.email}?subject=${encodeURIComponent(`Order ${order.order_number}`)}`} className={buttonClass({ variant: "outline" })}>
              <Mail aria-hidden="true" size={18} /> Email us
            </a>
          )}
          <ButtonLink href="/shop" variant="ghost">
            Continue shopping
          </ButtonLink>
        </div>
      </section>
    </div>
  );
}
