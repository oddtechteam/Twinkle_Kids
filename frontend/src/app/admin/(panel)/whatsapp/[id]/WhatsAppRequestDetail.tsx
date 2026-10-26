"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import {
  AdminPage,
  Card,
  ConfirmDialog,
  ErrorState,
  LoadingState,
  Pill,
  SelectInput,
  TextArea,
  TextInput,
  Toggle,
  adminStyles as styles,
} from "@/components/admin/Kit";
import { AddressFields, EMPTY_ADDRESS, addressErrors } from "@/components/checkout/AddressFields";
import { Button } from "@/components/ui/Button";
import { useMutation, useResource } from "@/lib/admin/hooks";
import { PAYMENT_METHOD_LABELS, WHATSAPP_STATUS_LABELS, type WhatsAppStatus, ordersApi, whatsappTone } from "@/lib/admin/orders";
import type { PaymentMethod, PostalAddress } from "@/lib/api/types";
import { formatDateTime, formatMoney } from "@/lib/format";

export function WhatsAppRequestDetail() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const request = useResource(() => ordersApi.whatsapp(id), id);
  const { run, pending } = useMutation();
  const [staffNote, setStaffNote] = useState<string | null>(null);
  const [confirmStatus, setConfirmStatus] = useState<WhatsAppStatus | null>(null);

  if (request.loading && !request.data) return <LoadingState label="Loading request…" />;
  if (request.error) return <ErrorState message={request.error} onRetry={request.reload} />;
  const r = request.data;
  if (!r) return null;
  const open = r.status === "initiated" || r.status === "contacted";

  async function setStatus(status: WhatsAppStatus) {
    const res = await run(() => ordersApi.setWhatsAppStatus(id, status, (staffNote ?? r?.staff_note ?? "").trim() || null), {
      success: `Marked “${WHATSAPP_STATUS_LABELS[status]}”`,
    });
    setConfirmStatus(null);
    if (res.ok) {
      request.setData(res.result);
      setStaffNote(null);
    }
  }

  return (
    <AdminPage
      title={`WhatsApp request ${r.reference}`}
      description={`Link handed out ${formatDateTime(r.created_at)}${r.contacted_at ? ` · customer message confirmed ${formatDateTime(r.contacted_at)}` : ""}`}
      breadcrumbs={[{ label: "WhatsApp requests", href: "/admin/whatsapp" }, { label: r.reference }]}
      actions={<Pill tone={whatsappTone(r.status)}>{WHATSAPP_STATUS_LABELS[r.status]}</Pill>}
    >
      <div className={styles.twoCol}>
        <div className={styles.stack}>
          <Card title="Requested items" hint="Prices are the estimate shown to the customer when they opened WhatsApp.">
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>SKU</th>
                    <th style={{ textAlign: "right" }}>Est. price</th>
                    <th style={{ textAlign: "right" }}>Qty</th>
                    <th style={{ textAlign: "right" }}>Est. total</th>
                  </tr>
                </thead>
                <tbody>
                  {r.lines.map((line, index) => (
                    <tr key={`${line.sku}-${index}`}>
                      <td data-label="Product">
                        <span className={styles.cellTitle}>{line.product_name}</span>
                        <span className={styles.muted}> {[line.size, line.colour].filter(Boolean).join(" · ")}</span>
                        {!line.variant_id && <span className={styles.warnText}> (option no longer exists)</span>}
                      </td>
                      <td data-label="SKU" className={styles.mono}>
                        {line.sku}
                      </td>
                      <td data-label="Est. price" className={styles.money}>
                        {formatMoney(line.unit_selling_price)}
                      </td>
                      <td data-label="Qty" className={styles.money}>
                        {line.quantity}
                      </td>
                      <td data-label="Est. total" className={styles.money}>
                        {formatMoney(line.line_total)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className={styles.grand} style={{ textAlign: "right", marginTop: "var(--space-3)" }}>
              Estimate {formatMoney(r.estimated_subtotal)}
            </p>
          </Card>

          <Card title="Pre-filled message" hint="What the customer's WhatsApp was filled with. They may have edited it — or not sent it.">
            <pre className={styles.message}>{r.message_text}</pre>
          </Card>

          {open && <ConvertForm requestId={id} lines={r.lines} defaultName={r.customer_name ?? ""} defaultPhone={r.customer_phone ?? ""} onConverted={(orderId) => router.push(`/admin/orders/${orderId}`)} />}
        </div>

        <div className={styles.stack}>
          <Card title="Status">
            {r.status === "converted" && r.converted_order_id ? (
              <p>
                Converted into order{" "}
                <Link href={`/admin/orders/${r.converted_order_id}`} className={styles.rowLink}>
                  {r.converted_order_number}
                </Link>
                .
              </p>
            ) : !open ? (
              <p className={styles.hint}>This request is {WHATSAPP_STATUS_LABELS[r.status].toLowerCase()}.</p>
            ) : (
              <div className={styles.stack}>
                <TextArea label="Staff note" value={staffNote ?? r.staff_note ?? ""} onChange={setStaffNote} maxLength={500} rows={3} />
                {r.status === "initiated" && (
                  <Button onClick={() => void setStatus("contacted")} loading={pending}>
                    Customer&apos;s message received
                  </Button>
                )}
                <Button variant="outline" onClick={() => setConfirmStatus("cancelled")} disabled={pending}>
                  Cancel request
                </Button>
                <Button variant="ghost" onClick={() => setConfirmStatus("expired")} disabled={pending}>
                  Mark expired (never heard back)
                </Button>
              </div>
            )}
          </Card>
          <Card title="Customer">
            <dl className={styles.kv}>
              <dt>Name</dt>
              <dd>{r.customer_name ?? "Not provided"}</dd>
              <dt>Account</dt>
              <dd>{r.user_id ? "Signed-in customer" : "Guest"}</dd>
            </dl>
            <p className={styles.hint}>Phone and address come from the WhatsApp chat itself — enter them when converting.</p>
          </Card>
        </div>
      </div>

      <ConfirmDialog
        open={confirmStatus !== null}
        title={confirmStatus === "cancelled" ? "Cancel this request?" : "Mark as expired?"}
        message="The request will be closed. No stock or payment is affected — requests never reserve stock."
        confirmLabel={confirmStatus === "cancelled" ? "Cancel request" : "Mark expired"}
        destructive
        pending={pending}
        onConfirm={() => confirmStatus && void setStatus(confirmStatus)}
        onClose={() => setConfirmStatus(null)}
      />
    </AdminPage>
  );
}

function ConvertForm({
  requestId,
  lines,
  defaultName,
  defaultPhone,
  onConverted,
}: {
  requestId: string;
  lines: { variant_id: string | null; product_name: string; size: string | null; colour: string | null; quantity: number }[];
  defaultName: string;
  defaultPhone: string;
  onConverted: (orderId: string) => void;
}) {
  const { run, pending } = useMutation();
  const [name, setName] = useState(defaultName);
  const [phone, setPhone] = useState(defaultPhone);
  const [email, setEmail] = useState("");
  const [address, setAddress] = useState<PostalAddress>({ ...EMPTY_ADDRESS, full_name: defaultName, phone: defaultPhone });
  const [method, setMethod] = useState<PaymentMethod | "">("");
  const [quantities, setQuantities] = useState<Record<string, number>>(
    Object.fromEntries(lines.filter((l) => l.variant_id).map((l) => [l.variant_id as string, l.quantity])),
  );
  const [applyShipping, setApplyShipping] = useState(true);
  const [note, setNote] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [confirming, setConfirming] = useState(false);

  function validate(): boolean {
    const found: Record<string, string> = { ...addressErrors(address) };
    if (!name.trim()) found.name = "Enter the customer's name.";
    if (phone.replace(/\D/g, "").length < 8) found.phone = "Enter the customer's phone.";
    if (!method) found.method = "Choose the agreed payment method.";
    if (!Object.values(quantities).some((q) => q > 0)) found.items = "At least one item needs a quantity.";
    setErrors(found);
    return Object.keys(found).length === 0;
  }

  async function convert() {
    const items = Object.entries(quantities)
      .filter(([, q]) => q > 0)
      .map(([variant_id, quantity]) => ({ variant_id, quantity }));
    const res = await run(
      () =>
        ordersApi.convertWhatsApp(requestId, {
          customer_name: name.trim(),
          customer_phone: phone.trim(),
          customer_email: email.trim() || null,
          address: { ...address, line2: address.line2 || null, landmark: address.landmark || null },
          payment_method: method as PaymentMethod,
          items,
          internal_note: note.trim() || null,
          apply_shipping: applyShipping,
        }),
      { success: "Order created from WhatsApp request" },
    );
    setConfirming(false);
    if (res.ok) onConverted(res.result.id);
  }

  return (
    <Card title="Convert to order" hint="Only after you've confirmed availability and price with the customer. Items are re-priced at today's catalogue prices and stock is deducted now.">
      <form
        className={styles.stack}
        noValidate
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          if (validate()) setConfirming(true);
        }}
      >
        <div className={styles.grid2}>
          <TextInput label="Customer name" value={name} onChange={setName} error={errors.name} required maxLength={120} />
          <TextInput label="Phone" value={phone} onChange={setPhone} error={errors.phone} required maxLength={20} type="tel" />
          <TextInput label="Email (optional)" value={email} onChange={setEmail} maxLength={254} type="email" />
          <SelectInput
            label="Agreed payment method"
            value={method}
            onChange={(v) => setMethod(v as PaymentMethod)}
            placeholder="Choose…"
            options={(Object.keys(PAYMENT_METHOD_LABELS) as PaymentMethod[]).map((m) => ({ value: m, label: PAYMENT_METHOD_LABELS[m] }))}
          />
        </div>
        {errors.method && <p className={styles.errorText}>{errors.method}</p>}
        <AddressFields value={address} onChange={setAddress} errors={errors} />
        <fieldset className={styles.stack} style={{ border: 0, padding: 0, margin: 0 }}>
          <legend className={styles.label}>Confirmed quantities</legend>
          {lines.map((line, index) =>
            line.variant_id ? (
              <label key={line.variant_id} className={styles.inlineRow}>
                <span>
                  {line.product_name} <span className={styles.muted}>{[line.size, line.colour].filter(Boolean).join(" · ")}</span>
                </span>
                <input
                  className={`${styles.input} ${styles.qtyInput}`}
                  type="number"
                  min={0}
                  max={99}
                  value={quantities[line.variant_id] ?? 0}
                  onChange={(e) => setQuantities({ ...quantities, [line.variant_id as string]: Math.max(0, Math.min(99, Number(e.target.value) || 0)) })}
                  aria-label={`Quantity for ${line.product_name}`}
                />
              </label>
            ) : (
              <p key={`gone-${index}`} className={styles.warnText}>
                {line.product_name} can no longer be ordered (option removed).
              </p>
            ),
          )}
          {errors.items && <p className={styles.errorText}>{errors.items}</p>}
        </fieldset>
        <Toggle label="Apply the shop's delivery charge rules" checked={applyShipping} onChange={setApplyShipping} />
        <TextArea label="Internal note (optional)" value={note} onChange={setNote} maxLength={500} rows={2} />
        <Button type="submit" disabled={pending}>
          Convert to order
        </Button>
      </form>
      <ConfirmDialog
        open={confirming}
        title="Create an order from this request?"
        message="Stock will be deducted and the order starts as “Pending confirmation” and unpaid. Record the payment on the order once you receive it."
        confirmLabel="Create order"
        pending={pending}
        onConfirm={() => void convert()}
        onClose={() => setConfirming(false)}
      />
    </Card>
  );
}
