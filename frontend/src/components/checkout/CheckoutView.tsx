"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { CircleAlert, Lock, RotateCcw, ShoppingBag, Tag } from "lucide-react";
import { type ComponentProps, type FormEvent, useCallback, useEffect, useId, useRef, useState } from "react";

import { useNavigationProgress } from "@/components/layout/NavigationProgress";
import { ProductImage } from "@/components/product/ProductImage";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Button, ButtonLink } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/Feedback";
import { Loader } from "@/components/ui/Loader";
import { fetchMe, listAddresses } from "@/lib/account/api";
import { ApiError } from "@/lib/api/client";
import type { CheckoutQuote, CustomerProfile, PaymentMethod, PostalAddress, SavedAddress } from "@/lib/api/types";
import { useBag } from "@/lib/bag/BagProvider";
import { checkPin,
  fetchQuote, placeOrder, rememberOrder } from "@/lib/checkout/api";
import { formatMoney } from "@/lib/format";
import { AddressFields, EMPTY_ADDRESS, addressErrors } from "./AddressFields";
import styles from "./CheckoutView.module.css";

const CRUMBS = [
  { label: "Home", href: "/" },
  { label: "Bag", href: "/bag" },
  { label: "Checkout" },
];
const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const PHONE = /^\+?[0-9][0-9 -]{6,18}$/;

function newKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
}

type Load = { status: "loading" } | { status: "error"; message: string } | { status: "ready"; quote: CheckoutQuote };

/**
 * Website checkout. Every amount shown comes from the server's quote; the order request carries
 * details and choices only, plus the total the shopper saw so the server can stop if it changed.
 */
export function CheckoutView({ delivery }: { delivery?: { message: string; estimate: string } }) {
  const bag = useBag();
  const router = useRouter();
  const progress = useNavigationProgress();
  const [load, setLoad] = useState<Load>({ status: "loading" });
  const [user, setUser] = useState<CustomerProfile | null>(null);
  const [addresses, setAddresses] = useState<SavedAddress[]>([]);
  const [addressChoice, setAddressChoice] = useState<string>("new");
  const [address, setAddress] = useState<PostalAddress>(EMPTY_ADDRESS);
  const [saveAddress, setSaveAddress] = useState(true);
  const [contact, setContact] = useState({ name: "", phone: "", email: "" });
  const [payment, setPayment] = useState<PaymentMethod | "">("");
  const [note, setNote] = useState("");
  const [couponInput, setCouponInput] = useState("");
  const [coupon, setCoupon] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const key = useRef<string>(newKey()); // one submission key per checkout attempt
  const errorSummary = useRef<HTMLDivElement>(null);
  const paymentGroup = useId();
  const [pinCheck, setPinCheck] = useState<{ pin: string; serviceable: boolean; message: string | null } | null>(null);
  const deliveryPin = (user && addressChoice !== "new" ? addresses.find((a) => a.id === addressChoice)?.postal_code : address.postal_code)?.trim() ?? "";

  // Advisory coverage check as the PIN is entered; placing the order checks again on the server.
  useEffect(() => {
    if (!/^[1-9]\d{5}$/.test(deliveryPin)) return;
    let live = true;
    const timer = setTimeout(() => {
      checkPin(deliveryPin)
        .then((result) => live && setPinCheck({ pin: deliveryPin, ...result }))
        .catch(() => undefined);
    }, 350);
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [deliveryPin]);
  const pinResult = pinCheck && pinCheck.pin === deliveryPin ? pinCheck : null;

  const refreshQuote = useCallback(async (code: string | null) => {
    try {
      const quote = await fetchQuote(code);
      setLoad({ status: "ready", quote });
      setPayment((current) => current || (quote.payment_methods.length === 1 ? quote.payment_methods[0]!.method : ""));
      return quote;
    } catch (error) {
      setLoad({ status: "error", message: error instanceof ApiError ? error.message : "We couldn't load your checkout." });
      return null;
    }
  }, []);

  useEffect(() => {
    void (async () => {
      const [me] = await Promise.all([fetchMe().catch(() => null), refreshQuote(null)]);
      if (!me) return;
      setUser(me);
      setContact((c) => ({ name: c.name || me.full_name, phone: c.phone || me.phone || "", email: c.email || me.email }));
      const saved = await listAddresses().catch(() => []);
      setAddresses(saved);
      const preferred = saved.find((a) => a.is_default) ?? saved[0];
      if (preferred) setAddressChoice(preferred.id);
    })();
  }, [refreshQuote]);

  if (load.status === "loading") return <Loader label="Preparing your checkout…" />;
  if (load.status === "error") {
    return (
      <div className={`container-narrow ${styles.page}`}>
        <Breadcrumbs items={CRUMBS} />
        <EmptyState
          tone="error"
          title="We couldn't load your checkout"
          description={load.message}
          action={
            <Button onClick={() => void refreshQuote(coupon)} iconStart={<RotateCcw aria-hidden="true" />}>
              Try again
            </Button>
          }
        />
      </div>
    );
  }

  const quote = load.quote;
  if (quote.bag.lines.length === 0) {
    return (
      <div className={`container-narrow ${styles.page}`}>
        <Breadcrumbs items={CRUMBS} />
        <EmptyState
          icon={<ShoppingBag aria-hidden="true" size={26} />}
          title="Your bag is empty"
          description="Add a few favourites before checking out."
          action={<ButtonLink href="/shop">Start shopping</ButtonLink>}
        />
      </div>
    );
  }

  const needsSignIn = !quote.signed_in && !quote.guest_checkout_enabled;
  const usingSaved = user !== null && addressChoice !== "new";

  function validate(): Record<string, string> {
    const found: Record<string, string> = {};
    if (!contact.name.trim()) found.name = "Enter your full name.";
    if (!PHONE.test(contact.phone.trim()) || contact.phone.replace(/\D/g, "").length < 8) {
      found.phone = "Enter a valid mobile number.";
    }
    if (!user && !EMAIL.test(contact.email.trim())) found.email = "Enter a valid email so we can send your order details.";
    if (user && contact.email.trim() && !EMAIL.test(contact.email.trim())) found.email = "Enter a valid email address.";
    if (!usingSaved) Object.assign(found, addressErrors(address));
    if (!payment) found.payment = "Choose how you'd like to pay.";
    return found;
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (submitting) return; // duplicate-click guard (the server is idempotent as well)
    const found = validate();
    setErrors(found);
    setSubmitError(null);
    if (Object.keys(found).length > 0) {
      requestAnimationFrame(() => errorSummary.current?.focus());
      return;
    }
    setSubmitting(true);
    try {
      const order = await placeOrder(
        {
          customer_name: contact.name.trim(),
          customer_phone: contact.phone.trim(),
          customer_email: contact.email.trim() || null,
          address: usingSaved ? null : address,
          saved_address_id: usingSaved ? addressChoice : null,
          payment_method: payment as PaymentMethod,
          customer_note: note.trim() || null,
          coupon_code: coupon,
          save_address: user !== null && !usingSaved && saveAddress,
          expected_grand_total: quote.grand_total,
        },
        key.current,
      );
      rememberOrder(order);
      void bag.refresh();
      progress.start(`/order-confirmation/${order.order_number}`);
      router.replace(`/order-confirmation/${encodeURIComponent(order.order_number)}`);
    } catch (error) {
      setSubmitting(false);
      if (error instanceof ApiError) {
        if (error.status === 409) {
          await refreshQuote(coupon); // prices or stock changed: show the new summary
        }
        setSubmitError(error.status >= 500 ? "Something went wrong on our side. Your order was not placed — please try again." : error.message);
      } else {
        setSubmitError("We couldn't reach the store. Please check your connection — your order was not placed.");
      }
      requestAnimationFrame(() => errorSummary.current?.focus());
    }
  }

  async function applyCoupon() {
    const code = couponInput.trim().toUpperCase() || null;
    const next = await refreshQuote(code);
    if (next && !next.coupon_error) setCoupon(next.coupon_code);
    else setCoupon(null);
  }

  const errorList = [...Object.values(errors), ...(submitError ? [submitError] : [])];

  return (
    <div className={`container ${styles.page}`}>
      <Breadcrumbs items={CRUMBS} />
      <h1 className={styles.title}>Checkout</h1>

      {!quote.can_place_order && quote.blocking_reason && (
        <div className={styles.blocking} role="status">
          <CircleAlert aria-hidden="true" size={20} />
          <p>{quote.blocking_reason}</p>
          {needsSignIn ? (
            <ButtonLink href="/account?next=/checkout" size="sm">
              Sign in
            </ButtonLink>
          ) : quote.bag.has_issues ? (
            <ButtonLink href="/bag" size="sm" variant="outline">
              Review bag
            </ButtonLink>
          ) : null}
        </div>
      )}

      <form className={styles.layout} onSubmit={submit} noValidate>
        <div className={styles.main}>
          {errorList.length > 0 && (
            <div ref={errorSummary} tabIndex={-1} className={styles.errorSummary} role="alert">
              <p className={styles.errorTitle}>Please check the following:</p>
              <ul>
                {errorList.map((message) => (
                  <li key={message}>{message}</li>
                ))}
              </ul>
            </div>
          )}

          <fieldset className={styles.section}>
            <legend className={styles.sectionTitle}>1. Contact details</legend>
            {!user && (
              <p className={styles.hint}>
                Have an account? <Link href="/account?next=/checkout">Sign in</Link> for saved addresses and order history.
              </p>
            )}
            <div className={styles.grid}>
              <Input label="Full name" value={contact.name} error={errors.name} autoComplete="name" onChange={(v) => setContact({ ...contact, name: v })} required />
              <Input label="Mobile number" value={contact.phone} error={errors.phone} type="tel" inputMode="tel" autoComplete="tel" onChange={(v) => setContact({ ...contact, phone: v })} required />
              <Input
                label={user ? "Email (optional)" : "Email"}
                hint={user ? `Order details go to ${user.email} if left blank.` : "We'll send your order details here."}
                value={contact.email}
                error={errors.email}
                type="email"
                autoComplete="email"
                onChange={(v) => setContact({ ...contact, email: v })}
                required={!user}
                wide
              />
            </div>
          </fieldset>

          <fieldset className={styles.section}>
            <legend className={styles.sectionTitle}>2. Delivery address</legend>
            {user && addresses.length > 0 && (
              <div className={styles.choices}>
                {addresses.map((saved) => (
                  <label key={saved.id} className={`${styles.choice} ${addressChoice === saved.id ? styles.chosen : ""}`}>
                    <input type="radio" name="address" checked={addressChoice === saved.id} onChange={() => setAddressChoice(saved.id)} />
                    <span>
                      <strong>{saved.label || saved.full_name}</strong>
                      <span className={styles.muted}>
                        {saved.line1}, {saved.city}, {saved.state} {saved.postal_code}
                      </span>
                    </span>
                  </label>
                ))}
                <label className={`${styles.choice} ${addressChoice === "new" ? styles.chosen : ""}`}>
                  <input type="radio" name="address" checked={addressChoice === "new"} onChange={() => setAddressChoice("new")} />
                  <span>
                    <strong>Use a new address</strong>
                  </span>
                </label>
              </div>
            )}
            {!usingSaved && (
              <>
                <AddressFields value={address} onChange={setAddress} errors={errors} />
                {user && (
                  <label className={styles.checkbox}>
                    <input type="checkbox" checked={saveAddress} onChange={(e) => setSaveAddress(e.target.checked)} />
                    Save this address to my account
                  </label>
                )}
              </>
            )}
            {pinResult && !pinResult.serviceable && (
              <p className={styles.warning} role="status">
                {pinResult.message || "Sorry, we don't deliver to this PIN code yet."}
              </p>
            )}
            {pinResult?.serviceable && (
              <p className={styles.hint} role="status">
                We deliver to {pinResult.pin}.{delivery?.estimate ? ` Estimated delivery: ${delivery.estimate} (the shop's estimate).` : ""}
              </p>
            )}
          </fieldset>

          <fieldset className={styles.section} aria-describedby={errors.payment ? `${paymentGroup}-error` : undefined}>
            <legend className={styles.sectionTitle}>3. Payment</legend>
            <p className={styles.hint}>
              <Lock aria-hidden="true" size={14} /> No card details are collected online. Choose how you&apos;ll pay — the shop confirms your order and payment
              details with you.
            </p>
            {quote.payment_methods.length === 0 ? (
              <p className={styles.warning}>No payment method is available right now, so orders can&apos;t be placed online.</p>
            ) : (
              <div className={styles.choices}>
                {quote.payment_methods.map((option) => (
                  <label key={option.method} className={`${styles.choice} ${payment === option.method ? styles.chosen : ""}`}>
                    <input type="radio" name={paymentGroup} checked={payment === option.method} onChange={() => setPayment(option.method)} />
                    <span>
                      <strong>{option.label}</strong>
                      {option.instructions && <span className={styles.muted}>{option.instructions}</span>}
                    </span>
                  </label>
                ))}
              </div>
            )}
            {errors.payment && (
              <p id={`${paymentGroup}-error`} className={styles.fieldError}>
                {errors.payment}
              </p>
            )}
          </fieldset>

          <fieldset className={styles.section}>
            <legend className={styles.sectionTitle}>4. Order notes (optional)</legend>
            <label className={styles.field}>
              <span className="visually-hidden">Order notes</span>
              <textarea className={styles.textarea} rows={3} maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Gift message, delivery instructions…" />
            </label>
          </fieldset>
        </div>

        <aside className={styles.summary} aria-labelledby="checkout-summary">
          <h2 id="checkout-summary" className={styles.summaryTitle}>
            Order summary
          </h2>
          <ul className={styles.items}>
            {quote.bag.lines.map((line) => (
              <li key={line.item_id} className={styles.item}>
                <div className={styles.thumb}>
                  <ProductImage image={line.image} name={line.product_name} seed={line.product_slug ?? line.item_id} sizes="64px" />
                  <span className={styles.qty} aria-label={`Quantity ${line.quantity}`}>
                    {line.quantity}
                  </span>
                </div>
                <div className={styles.itemInfo}>
                  <p className={styles.itemName}>{line.product_name}</p>
                  <p className={styles.muted}>
                    {[line.size && `Size ${line.size}`, line.colour].filter(Boolean).join(" · ")}
                    {line.price && ` · ${formatMoney(line.price.selling_price)} each`}
                  </p>
                  {line.issue && <p className={styles.fieldError}>{line.issue}</p>}
                </div>
                <p className={styles.itemTotal}>{line.line_total ? formatMoney(line.line_total) : "—"}</p>
              </li>
            ))}
          </ul>

          {/* Not a nested form: Enter in the coupon box applies the code, not the order. */}
          <div className={styles.coupon}>
            <label className={styles.couponLabel}>
              <Tag aria-hidden="true" size={16} />
              <span className="visually-hidden">Coupon code</span>
              <input
                value={couponInput}
                onChange={(e) => setCouponInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    void applyCoupon();
                  }
                }}
                placeholder="Coupon code"
                maxLength={40}
                autoCapitalize="characters"
              />
            </label>
            <Button type="button" size="sm" variant="soft" onClick={() => void applyCoupon()} disabled={!couponInput.trim()}>
              Apply
            </Button>
          </div>
          {quote.coupon_error && (
            <p className={styles.fieldError} role="status">
              {quote.coupon_error}
            </p>
          )}
          {coupon && !quote.coupon_error && (
            <p className={styles.applied} role="status">
              {coupon} applied.{" "}
              <button
                type="button"
                className={styles.linkButton}
                onClick={() => {
                  setCoupon(null);
                  setCouponInput("");
                  void refreshQuote(null);
                }}
              >
                Remove
              </button>
            </p>
          )}

          <dl className={styles.totals}>
            <dt>Subtotal</dt>
            <dd>{formatMoney(quote.subtotal)}</dd>
            {Number(quote.discount_total) > 0 && (
              <>
                <dt>Discount{quote.coupon_code ? ` (${quote.coupon_code})` : ""}</dt>
                <dd className={styles.discount}>−{formatMoney(quote.discount_total)}</dd>
              </>
            )}
            <dt>Delivery</dt>
            <dd>
              {!quote.shipping_configured
                ? "Confirmed by the shop"
                : Number(quote.shipping_total) === 0
                  ? "Free"
                  : formatMoney(quote.shipping_total)}
            </dd>
            <dt className={styles.grand}>Total</dt>
            <dd className={styles.grand}>{formatMoney(quote.grand_total)}</dd>
          </dl>
          {!quote.shipping_configured && (
            <p className={styles.hint}>Any delivery charge will be confirmed by the shop before dispatch.</p>
          )}
          {delivery?.message && <p className={styles.hint}>{delivery.message}</p>}

          <Button type="submit" size="lg" fullWidth loading={submitting} disabled={!quote.can_place_order || submitting}>
            Place order
          </Button>
          <p className={styles.hint}>
            Placing an order doesn&apos;t take a payment. Your order stays unpaid until the shop records your payment.
          </p>
        </aside>
      </form>
    </div>
  );
}

function Input({
  label,
  value,
  onChange,
  error,
  hint,
  wide = false,
  ...rest
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  hint?: string;
  wide?: boolean;
} & Omit<ComponentProps<"input">, "value" | "onChange">) {
  const id = useId();
  return (
    <div className={`${styles.field} ${wide ? styles.wide : ""}`}>
      <label htmlFor={id} className={styles.label}>
        {label}
        {rest.required && <span aria-hidden="true"> *</span>}
      </label>
      <input
        id={id}
        className={`${styles.input} ${error ? styles.invalid : ""}`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}
        {...rest}
      />
      {error ? (
        <p id={`${id}-error`} className={styles.fieldError}>
          {error}
        </p>
      ) : (
        hint && (
          <p id={`${id}-hint`} className={styles.hint}>
            {hint}
          </p>
        )
      )}
    </div>
  );
}
