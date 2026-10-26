"use client";

import { useParams } from "next/navigation";
import { useState } from "react";

import {
  AdminPage,
  Card,
  ConfirmDialog,
  ErrorState,
  LoadingState,
  Pill,
  SelectInput,
  TextArea,
  adminStyles as styles,
} from "@/components/admin/Kit";
import { Button } from "@/components/ui/Button";
import { useMutation, useResource } from "@/lib/admin/hooks";
import {
  ORDER_STATUS_LABELS,
  ORDER_TRANSITIONS,
  type OrderStatus,
  PAYMENT_METHOD_LABELS,
  PAYMENT_STATUS_LABELS,
  type PaymentStatus,
  ordersApi,
  paymentTone,
  statusTone,
} from "@/lib/admin/orders";
import type { PaymentMethod } from "@/lib/api/types";
import { formatDateTime, formatMoney } from "@/lib/format";

export function OrderDetail() {
  const { id } = useParams<{ id: string }>();
  const order = useResource(() => ordersApi.get(id), id);
  const { run, pending } = useMutation();
  const [nextStatus, setNextStatus] = useState<OrderStatus | "">("");
  const [paymentStatus, setPaymentStatus] = useState<PaymentStatus | "">("");
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod | "">("");
  const [note, setNote] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<"status" | "payment" | null>(null);

  if (order.loading && !order.data) return <LoadingState label="Loading order…" />;
  if (order.error) return <ErrorState message={order.error} onRetry={order.reload} />;
  const o = order.data;
  if (!o) return null;

  const allowed = ORDER_TRANSITIONS[o.status];
  const address = o.shipping_address;
  const restocks = nextStatus === "cancelled" || nextStatus === "returned";

  async function applyStatus() {
    if (!nextStatus) return;
    const res = await run(() => ordersApi.setStatus(id, nextStatus), { success: `Order marked ${ORDER_STATUS_LABELS[nextStatus].toLowerCase()}` });
    setConfirm(null);
    if (res.ok) {
      order.setData(res.result);
      setNextStatus("");
    }
  }

  async function applyPayment() {
    if (!paymentStatus) return;
    const res = await run(() => ordersApi.recordPayment(id, paymentStatus, paymentMethod || null), { success: "Payment record updated" });
    setConfirm(null);
    if (res.ok) {
      order.setData(res.result);
      setPaymentStatus("");
      setPaymentMethod("");
    }
  }

  async function saveNote() {
    const res = await run(() => ordersApi.setNote(id, (note ?? "").trim() || null), { success: "Internal note saved" });
    if (res.ok) {
      order.setData(res.result);
      setNote(null);
    }
  }

  return (
    <AdminPage
      title={`Order ${o.order_number}`}
      description={`Placed ${formatDateTime(o.placed_at)} · ${o.source === "whatsapp" ? "Confirmed WhatsApp order" : "Website order"}`}
      breadcrumbs={[{ label: "Orders", href: "/admin/orders" }, { label: o.order_number }]}
      actions={
        <>
          <Pill tone={statusTone(o.status)}>{ORDER_STATUS_LABELS[o.status]}</Pill>
          <Pill tone={paymentTone(o.payment_status)}>{PAYMENT_STATUS_LABELS[o.payment_status]}</Pill>
        </>
      }
    >
      <div className={styles.twoCol}>
        <div className={styles.stack}>
          <Card title="Items">
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>SKU</th>
                    <th style={{ textAlign: "right" }}>Price</th>
                    <th style={{ textAlign: "right" }}>Qty</th>
                    <th style={{ textAlign: "right" }}>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {o.lines.map((line, index) => (
                    <tr key={`${line.sku}-${index}`}>
                      <td data-label="Product">
                        <span className={styles.cellTitle}>{line.product_name}</span>
                        <span className={styles.muted}> {[line.size, line.colour].filter(Boolean).join(" · ")}</span>
                      </td>
                      <td data-label="SKU" className={styles.mono}>
                        {line.sku}
                      </td>
                      <td data-label="Price" className={styles.money}>
                        {formatMoney(line.unit_selling_price)}
                        {line.unit_original_price && line.unit_original_price !== line.unit_selling_price && (
                          <span className={styles.muted}>
                            {" "}
                            <s>{formatMoney(line.unit_original_price)}</s>
                          </span>
                        )}
                      </td>
                      <td data-label="Qty" className={styles.money}>
                        {line.quantity}
                      </td>
                      <td data-label="Total" className={styles.money}>
                        {formatMoney(line.line_total)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <dl className={styles.kv} style={{ marginTop: "var(--space-4)" }}>
              <dt>Subtotal</dt>
              <dd className={styles.money}>{formatMoney(o.subtotal)}</dd>
              {Number(o.discount_total) > 0 && (
                <>
                  <dt>Discount {o.coupon_code ? `(${o.coupon_code})` : ""}</dt>
                  <dd className={styles.money}>−{formatMoney(o.discount_total)}</dd>
                </>
              )}
              <dt>Delivery</dt>
              <dd className={styles.money}>{formatMoney(o.shipping_total)}</dd>
              <dt className={styles.grand}>Order total</dt>
              <dd className={`${styles.money} ${styles.grand}`}>{formatMoney(o.grand_total)}</dd>
            </dl>
            <p className={styles.hint}>Prices are a snapshot from when the order was placed; later catalogue edits don&apos;t change them.</p>
          </Card>

          <Card title="Customer & delivery">
            <dl className={styles.kv}>
              <dt>Name</dt>
              <dd>{o.customer_name}</dd>
              <dt>Phone</dt>
              <dd>
                <a href={`tel:${o.customer_phone.replace(/[^\d+]/g, "")}`}>{o.customer_phone}</a>
              </dd>
              <dt>Email</dt>
              <dd>{o.customer_email ? <a href={`mailto:${o.customer_email}`}>{o.customer_email}</a> : "—"}</dd>
              <dt>Account</dt>
              <dd>{o.user_id ? "Registered customer" : "Guest checkout"}</dd>
              <dt>Deliver to</dt>
              <dd>
                {address.full_name}, {address.line1}
                {address.line2 ? `, ${address.line2}` : ""}
                {address.landmark ? ` (near ${address.landmark})` : ""}, {address.city}, {address.state} {address.postal_code} · {address.phone}
              </dd>
              {o.customer_note && (
                <>
                  <dt>Customer note</dt>
                  <dd>{o.customer_note}</dd>
                </>
              )}
            </dl>
          </Card>
        </div>

        <div className={styles.stack}>
          <Card title="Order status" hint="Internal workflow for the team. Customers never see a tracking timeline.">
            {allowed.length === 0 ? (
              <p className={styles.hint}>This order is {ORDER_STATUS_LABELS[o.status].toLowerCase()} — no further changes.</p>
            ) : (
              <div className={styles.stack}>
                <SelectInput
                  label="Move to"
                  value={nextStatus}
                  onChange={(v) => setNextStatus(v as OrderStatus)}
                  placeholder="Choose a status"
                  options={allowed.map((s) => ({ value: s, label: ORDER_STATUS_LABELS[s] }))}
                />
                {restocks && <p className={styles.warnText}>The ordered quantities will be added back to stock.</p>}
                <Button onClick={() => setConfirm("status")} disabled={!nextStatus || pending}>
                  Update status
                </Button>
              </div>
            )}
          </Card>

          <Card title="Payment" hint="No payment gateway: record what you actually received.">
            <dl className={styles.kv}>
              <dt>Method chosen</dt>
              <dd>{o.payment_method ? PAYMENT_METHOD_LABELS[o.payment_method] : "—"}</dd>
              <dt>Recorded</dt>
              <dd>{PAYMENT_STATUS_LABELS[o.payment_status]}</dd>
            </dl>
            <div className={styles.stack} style={{ marginTop: "var(--space-4)" }}>
              <SelectInput
                label="Payment status"
                value={paymentStatus}
                onChange={(v) => setPaymentStatus(v as PaymentStatus)}
                placeholder="Choose…"
                options={(Object.keys(PAYMENT_STATUS_LABELS) as PaymentStatus[])
                  .filter((s) => s !== o.payment_status)
                  .map((s) => ({ value: s, label: PAYMENT_STATUS_LABELS[s] }))}
              />
              <SelectInput
                label="Received via (optional)"
                value={paymentMethod}
                onChange={(v) => setPaymentMethod(v as PaymentMethod)}
                placeholder="Keep current method"
                options={(Object.keys(PAYMENT_METHOD_LABELS) as PaymentMethod[]).map((m) => ({ value: m, label: PAYMENT_METHOD_LABELS[m] }))}
              />
              <Button variant="outline" onClick={() => setConfirm("payment")} disabled={!paymentStatus || pending}>
                Record payment update
              </Button>
            </div>
          </Card>

          <Card title="Internal note" hint="Only visible to staff.">
            <TextArea label="Note" value={note ?? o.internal_note ?? ""} onChange={setNote} maxLength={500} rows={4} />
            <Button variant="outline" onClick={() => void saveNote()} disabled={note === null || pending}>
              Save note
            </Button>
          </Card>
        </div>
      </div>

      <ConfirmDialog
        open={confirm === "status"}
        title="Update order status?"
        message={
          nextStatus
            ? `Move ${o.order_number} from “${ORDER_STATUS_LABELS[o.status]}” to “${ORDER_STATUS_LABELS[nextStatus]}”.${restocks ? " Stock will be added back." : ""}`
            : ""
        }
        confirmLabel="Update status"
        destructive={nextStatus === "cancelled"}
        pending={pending}
        onConfirm={() => void applyStatus()}
        onClose={() => setConfirm(null)}
      />
      <ConfirmDialog
        open={confirm === "payment"}
        title="Record this payment update?"
        message={
          paymentStatus
            ? `Only record “${PAYMENT_STATUS_LABELS[paymentStatus]}” if the money has actually been received or refunded. This is logged in the audit trail.`
            : ""
        }
        confirmLabel="Record update"
        pending={pending}
        onConfirm={() => void applyPayment()}
        onClose={() => setConfirm(null)}
      />
    </AdminPage>
  );
}
