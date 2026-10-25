"use client";

import Link from "next/link";
import { CircleAlert, MessageCircle, RotateCcw, ShoppingBag, Trash2 } from "lucide-react";
import { useState } from "react";

import { ProductImage } from "@/components/product/ProductImage";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Button, ButtonLink } from "@/components/ui/Button";
import { EmptyState, Skeleton } from "@/components/ui/Feedback";
import { Price } from "@/components/ui/Price";
import { QuantityStepper } from "@/components/ui/QuantityStepper";
import { useToast } from "@/components/ui/Toast";
import type { Cart, CartLine } from "@/lib/api/types";
import { useBag } from "@/lib/bag/BagProvider";
import { bagErrorMessage, startWhatsAppRequest } from "@/lib/bag/api";
import { formatMoney, plural } from "@/lib/format";
import styles from "./BagView.module.css";

const CRUMBS = [{ label: "Home", href: "/" }, { label: "Shopping bag" }];

/**
 * The shopping bag. Everything shown — prices, savings, delivery and totals — is exactly what
 * the cart API calculated; this component only sends quantity changes.
 */
export function BagView({ whatsappEnabled }: { whatsappEnabled: boolean }) {
  const bag = useBag();

  if (bag.status === "loading" && !bag.cart) return <BagSkeleton />;
  if (bag.status === "error" && !bag.cart) {
    return (
      <div className={`container-narrow ${styles.page}`}>
        <Breadcrumbs items={CRUMBS} />
        <EmptyState
          tone="error"
          title="We couldn't load your bag"
          description="Please check your connection and try again."
          action={
            <Button onClick={() => void bag.refresh()} iconStart={<RotateCcw aria-hidden="true" />}>
              Try again
            </Button>
          }
        />
      </div>
    );
  }

  const cart = bag.cart;
  if (!cart || cart.lines.length === 0) {
    return (
      <div className={`container-narrow ${styles.page}`}>
        <Breadcrumbs items={CRUMBS} />
        <EmptyState
          icon={<ShoppingBag aria-hidden="true" size={26} />}
          title="Your bag is empty"
          description="Find something lovely for your little one — it will wait here for you."
          action={
            <>
              <ButtonLink href="/shop">Start shopping</ButtonLink>
              <ButtonLink href="/wishlist" variant="outline">
                View wishlist
              </ButtonLink>
            </>
          }
        />
      </div>
    );
  }

  return (
    <div className={`container ${styles.page}`}>
      <Breadcrumbs items={CRUMBS} />
      <h1 className={styles.title}>
        Your bag <span className={styles.count}>({plural(cart.item_count, "item")})</span>
      </h1>

      {cart.has_price_changes && <PriceChangeNotice />}

      <div className={styles.layout}>
        <ul className={styles.lines} aria-label="Items in your bag">
          {cart.lines.map((line) => (
            <BagLine key={line.item_id} line={line} />
          ))}
        </ul>
        <Summary cart={cart} whatsappEnabled={whatsappEnabled} />
      </div>
    </div>
  );
}

function PriceChangeNotice() {
  const bag = useBag();
  const [busy, setBusy] = useState(false);
  return (
    <div className={styles.notice} role="status">
      <CircleAlert aria-hidden="true" size={20} />
      <p>Some prices have changed since you added these items. Your bag shows the current prices.</p>
      <Button
        size="sm"
        variant="soft"
        loading={busy}
        onClick={async () => {
          setBusy(true);
          await bag.acknowledgePrices();
          setBusy(false);
        }}
      >
        Got it
      </Button>
    </div>
  );
}

function BagLine({ line }: { line: CartLine }) {
  const bag = useBag();
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const options = [line.size && `Size ${line.size}`, line.colour].filter(Boolean).join(" · ");
  const href = line.product_slug ? `/products/${line.product_slug}` : null;
  const upper = Math.max(line.quantity, line.max_quantity);

  async function change(action: () => ReturnType<typeof bag.update>, failure: string) {
    setBusy(true);
    const result = await action();
    setBusy(false);
    if (!result.ok) toast.show({ tone: "warning", title: failure, description: result.message });
  }

  return (
    <li className={`${styles.line} ${line.available ? "" : styles.attention}`} aria-busy={busy}>
      <div className={styles.thumb}>
        <ProductImage image={line.image} name={line.product_name} seed={line.product_slug ?? line.item_id} sizes="112px" />
      </div>
      <div className={styles.info}>
        <p className={styles.name}>
          {href ? (
            <Link href={href} className={styles.nameLink}>
              {line.product_name}
            </Link>
          ) : (
            line.product_name
          )}
        </p>
        {options && <p className={styles.options}>{options}</p>}
        {line.sku && <p className={styles.sku}>SKU {line.sku}</p>}
        {line.price && <Price price={line.price} size="sm" />}
        {line.previous_price && (
          <p className={styles.changed}>Price updated (was {formatMoney(line.previous_price)})</p>
        )}
        {line.issue && (
          <p className={styles.issue} role="status">
            <CircleAlert aria-hidden="true" size={16} /> {line.issue}
          </p>
        )}
        <div className={styles.controls}>
          {line.max_quantity > 0 && (
            <QuantityStepper
              size="sm"
              value={line.quantity}
              max={upper}
              label={`Quantity for ${line.product_name}`}
              disabled={busy}
              onChange={(quantity) =>
                void change(() => bag.update(line.item_id, quantity), "Couldn't update the quantity")
              }
            />
          )}
          <Button
            variant="link"
            size="sm"
            disabled={busy}
            iconStart={<Trash2 aria-hidden="true" size={16} />}
            onClick={() => void change(() => bag.remove(line.item_id), "Couldn't remove the item")}
            aria-label={`Remove ${line.product_name} from your bag`}
          >
            Remove
          </Button>
        </div>
      </div>
      <p className={styles.lineTotal}>
        {line.line_total !== null ? formatMoney(line.line_total) : <span className={styles.muted}>—</span>}
      </p>
    </li>
  );
}

function Summary({ cart, whatsappEnabled }: { cart: Cart; whatsappEnabled: boolean }) {
  const toast = useToast();
  const [opening, setOpening] = useState(false);
  const orderable = cart.lines.filter((line) => line.available);
  const savings = Number(cart.savings) > 0;

  async function orderOnWhatsApp() {
    const tab = window.open("", "_blank"); // inside the click, so pop-up blockers allow it
    setOpening(true);
    try {
      const link = await startWhatsAppRequest(
        orderable.map((line) => ({ variantId: line.variant_id, quantity: line.quantity })),
      );
      if (tab) {
        tab.opener = null;
        tab.location.href = link.url;
      } else {
        window.location.href = link.url;
      }
      toast.show({
        tone: "info",
        title: "Continue in WhatsApp",
        description: `Send the pre-filled message to place your request (ref. ${link.reference}). Your bag stays here until your order is confirmed.`,
      });
    } catch (error) {
      tab?.close();
      toast.show({ tone: "warning", title: "Couldn't open WhatsApp", description: bagErrorMessage(error) });
    } finally {
      setOpening(false);
    }
  }

  return (
    <aside className={styles.summary} aria-labelledby="bag-summary-title">
      <h2 id="bag-summary-title" className={styles.summaryTitle}>
        Order summary
      </h2>
      <dl className={styles.totals}>
        <dt>Subtotal</dt>
        <dd>{formatMoney(cart.subtotal)}</dd>
        {savings && (
          <>
            <dt>You save</dt>
            <dd className={styles.saving}>{formatMoney(cart.savings)}</dd>
          </>
        )}
        <dt>Delivery</dt>
        <dd>
          {cart.shipping_total === null
            ? "Confirmed with your order"
            : Number(cart.shipping_total) === 0
              ? "Free"
              : formatMoney(cart.shipping_total)}
        </dd>
        <dt className={styles.grand}>Total</dt>
        <dd className={styles.grand}>{formatMoney(cart.grand_total)}</dd>
      </dl>
      {cart.has_issues && (
        <p className={styles.summaryNote}>Items that need attention aren&apos;t included in the total.</p>
      )}

      <div className={styles.summaryActions}>
        {whatsappEnabled && (
          <Button
            fullWidth
            size="lg"
            onClick={() => void orderOnWhatsApp()}
            loading={opening}
            disabled={orderable.length === 0}
            iconStart={<MessageCircle aria-hidden="true" />}
          >
            Order on WhatsApp
          </Button>
        )}
        <p className={styles.summaryNote}>
          {whatsappEnabled
            ? "We'll confirm availability, delivery and payment with you on WhatsApp. Online checkout is coming soon."
            : "Online checkout is coming soon. Your bag is saved for you until then."}
        </p>
        <ButtonLink href="/shop" variant="outline" fullWidth>
          Continue shopping
        </ButtonLink>
      </div>
    </aside>
  );
}

function BagSkeleton() {
  return (
    <div className={`container ${styles.page}`} aria-busy="true" aria-label="Loading your bag">
      <Skeleton width="10rem" height="0.9rem" />
      <div className={styles.layout} style={{ marginTop: "var(--space-6)" }}>
        <div className={styles.lines}>
          {[0, 1].map((i) => (
            <Skeleton key={i} height="8rem" radius="var(--radius-lg)" />
          ))}
        </div>
        <Skeleton height="16rem" radius="var(--radius-lg)" />
      </div>
    </div>
  );
}
