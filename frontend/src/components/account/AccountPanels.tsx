"use client";

import { MapPin, Package, Pencil, Plus, Trash2 } from "lucide-react";
import { type FormEvent, useCallback, useEffect, useState } from "react";

import { AddressFields, EMPTY_ADDRESS, addressErrors } from "@/components/checkout/AddressFields";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { EmptyState } from "@/components/ui/Feedback";
import { ChoiceChip, Select, TextField } from "@/components/ui/Form";
import { Loader } from "@/components/ui/Loader";
import { useToast } from "@/components/ui/Toast";
import {
  type MyOrderRequest,
  type OrderRequestKind,
  addAddress,
  changePassword,
  createOrderRequest,
  deleteAddress,
  fetchMyOrder,
  listAddresses,
  listMyOrders,
  listOrderRequests,
  updateAddress,
  updateProfile,
} from "@/lib/account/api";
import { ApiError } from "@/lib/api/client";
import type { CustomerOrder, CustomerOrderList, CustomerProfile, PostalAddress, SavedAddress } from "@/lib/api/types";
import type { OrderPolicy } from "@/lib/content/types";
import { formatDateTime, formatMoney, plural } from "@/lib/format";
import styles from "./AccountView.module.css";

function message(error: unknown): string {
  if (error instanceof ApiError) return error.status >= 500 ? "Something went wrong. Please try again." : error.message;
  return "We couldn't reach the store. Check your connection and try again.";
}

// --- orders (history only — no tracking) -------------------------------------------------------

export function OrdersPanel({ policy }: { policy: OrderPolicy | null }) {
  const [state, setState] = useState<{ status: "loading" } | { status: "error"; message: string } | { status: "ready"; data: CustomerOrderList }>({
    status: "loading",
  });
  const [page, setPage] = useState(1);
  const [open, setOpen] = useState<CustomerOrder | null>(null);
  const [opening, setOpening] = useState<string | null>(null);
  const toast = useToast();

  const load = useCallback(async (target: number) => {
    setState({ status: "loading" });
    try {
      setState({ status: "ready", data: await listMyOrders(target) });
    } catch (error) {
      setState({ status: "error", message: message(error) });
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads external data (API / session storage) on mount
    void load(page);
  }, [load, page]);

  async function view(reference: string) {
    setOpening(reference);
    try {
      setOpen(await fetchMyOrder(reference));
    } catch (error) {
      toast.show({ tone: "warning", title: "Couldn't open that order", description: message(error) });
    } finally {
      setOpening(null);
    }
  }

  return (
    <section className={styles.panel} aria-labelledby="orders-title">
      <h2 id="orders-title" className={styles.panelTitle}>
        My orders
      </h2>
      <p className={styles.muted}>For updates on an order, contact us with its reference — we&apos;re happy to help.</p>
      {state.status === "loading" && <Loader variant="inline" label="Loading your orders…" />}
      {state.status === "error" && (
        <EmptyState tone="error" title="We couldn't load your orders" description={state.message} action={<Button onClick={() => void load(page)}>Try again</Button>} />
      )}
      {state.status === "ready" && state.data.items.length === 0 && (
        <EmptyState icon={<Package aria-hidden="true" size={24} />} title="No orders yet" description="Orders you place while signed in will appear here." action={<ButtonLink href="/shop">Start shopping</ButtonLink>} />
      )}
      {state.status === "ready" && state.data.items.length > 0 && (
        <>
          <ul className={styles.list}>
            {state.data.items.map((order) => (
              <li key={order.order_number} className={styles.row}>
                <div className={styles.rowMain}>
                  <span className={styles.strong}>{order.order_number}</span>
                  <span className={styles.muted}>
                    {formatDateTime(order.placed_at)} · {plural(order.item_count, "item")}
                  </span>
                </div>
                <div className={styles.rowActions}>
                  <span className={styles.strong}>{formatMoney(order.grand_total)}</span>
                  <Button size="sm" variant="soft" loading={opening === order.order_number} onClick={() => void view(order.order_number)}>
                    View
                  </Button>
                </div>
              </li>
            ))}
          </ul>
          {state.data.pages > 1 && (
            <div className={styles.rowActions}>
              <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                Newer
              </Button>
              <span className={styles.muted}>
                Page {page} of {state.data.pages}
              </span>
              <Button size="sm" variant="outline" disabled={page >= state.data.pages} onClick={() => setPage(page + 1)}>
                Older
              </Button>
            </div>
          )}
        </>
      )}

      {open && (
        <Dialog open onClose={() => setOpen(null)} title={`Order ${open.order_number}`}>
          <div className={styles.formStack}>
            <p className={styles.muted}>Placed {formatDateTime(open.placed_at)}</p>
            <ul className={styles.orderLines}>
              {open.lines.map((line, index) => (
                <li key={`${line.sku}-${index}`} className={styles.orderLine}>
                  <span>
                    {line.product_name}
                    <span className={styles.muted}>
                      {" "}
                      {[line.size, line.colour].filter(Boolean).join(" · ")} × {line.quantity}
                    </span>
                  </span>
                  <span>{formatMoney(line.line_total)}</span>
                </li>
              ))}
            </ul>
            <dl className={styles.details}>
              <dt>Subtotal</dt>
              <dd>{formatMoney(open.subtotal)}</dd>
              {Number(open.discount_total) > 0 && (
                <>
                  <dt>Discount</dt>
                  <dd>−{formatMoney(open.discount_total)}</dd>
                </>
              )}
              <dt>Delivery</dt>
              <dd>{formatMoney(open.shipping_total)}</dd>
              <dt>Total</dt>
              <dd className={styles.strong}>{formatMoney(open.grand_total)}</dd>
            </dl>
            <p className={styles.muted}>
              <MapPin aria-hidden="true" size={14} /> {open.shipping_address.line1}, {open.shipping_address.city}, {open.shipping_address.state}{" "}
              {open.shipping_address.postal_code}
            </p>
            <OrderRequests key={open.order_number} orderNumber={open.order_number} policy={policy} />
            <ButtonLink href="/contact" variant="outline">
              Contact us about this order
            </ButtonLink>
          </div>
        </Dialog>
      )}
    </section>
  );
}

// --- cancellation / return / exchange requests ------------------------------------------------

const KIND_LABELS: Record<OrderRequestKind, string> = { cancellation: "Cancel order", return: "Return", exchange: "Exchange" };
const REQUEST_STATUS: Record<MyOrderRequest["status"], string> = {
  requested: "Waiting for the shop",
  approved: "Approved",
  rejected: "Declined",
  received: "Items received",
  completed: "Completed",
};

/** Requests under the shop's policy. Eligibility (order stage, return window) is checked by the
 *  server, which explains when a request isn't possible; refunds are arranged by the shop. */
function OrderRequests({ orderNumber, policy }: { orderNumber: string; policy: OrderPolicy | null }) {
  const kinds = (
    [
      ["cancellation", policy?.cancellation],
      ["return", policy?.returns],
      ["exchange", policy?.exchanges],
    ] as const
  )
    .filter(([, enabled]) => enabled)
    .map(([kind]) => kind);
  const [requests, setRequests] = useState<MyOrderRequest[] | null>(null);
  const [kind, setKind] = useState<OrderRequestKind | null>(null);
  const [reason, setReason] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const toast = useToast();

  useEffect(() => {
    let live = true;
    listOrderRequests(orderNumber)
      .then((items) => live && setRequests(items))
      .catch(() => live && setRequests([]));
    return () => {
      live = false;
    };
  }, [orderNumber]);

  if (kinds.length === 0 && (requests === null || requests.length === 0)) return null;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!kind || !reason) {
      setError("Choose what you'd like and a reason.");
      return;
    }
    setPending(true);
    setError(null);
    try {
      const created = await createOrderRequest(orderNumber, { kind, reason, message: note.trim() || null });
      setRequests((current) => [created, ...(current ?? [])]);
      setKind(null);
      setReason("");
      setNote("");
      toast.show({ title: "Request sent", description: `Reference ${created.reference}. The shop will review it.` });
    } catch (e) {
      setError(message(e));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className={styles.requests}>
      <p className={styles.strong}>Cancellations, returns &amp; exchanges</p>
      {requests && requests.length > 0 && (
        <ul className={styles.list}>
          {requests.map((r) => (
            <li key={r.reference} className={styles.requestItem}>
              <span className={styles.strong}>
                {KIND_LABELS[r.kind]} · {REQUEST_STATUS[r.status]}
              </span>
              <span className={styles.muted}>
                {r.reference} · {formatDateTime(r.created_at)} · {r.reason}
              </span>
              {r.resolution_note && <span>Shop: {r.resolution_note}</span>}
            </li>
          ))}
        </ul>
      )}
      {kinds.length > 0 && (
        <form className={styles.formStack} onSubmit={submit} noValidate>
          <div className={styles.kindChoice} role="radiogroup" aria-label="What would you like?">
            {kinds.map((k) => (
              <ChoiceChip key={k} type="radio" name="request-kind" label={KIND_LABELS[k]} checked={kind === k} onChange={() => setKind(k)} />
            ))}
          </div>
          {kind && (
            <>
              <Select label="Reason" value={reason} onChange={(e) => setReason(e.target.value)} required>
                <option value="">Choose a reason</option>
                {(policy?.reasons ?? []).map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </Select>
              <label>
                <span className={styles.muted}>Anything else we should know? (optional)</span>
                <textarea className={styles.textarea} rows={3} maxLength={1000} value={note} onChange={(e) => setNote(e.target.value)} />
              </label>
              {kind !== "cancellation" && policy && (
                <p className={styles.muted}>
                  Returns and exchanges can be requested once the order is delivered, within {policy.returnWindowDays} days of the order date.
                </p>
              )}
              {policy?.note && <p className={styles.muted}>{policy.note}</p>}
              {error && (
                <p className={styles.muted} role="alert">
                  {error}
                </p>
              )}
              <Button type="submit" loading={pending}>
                Send request
              </Button>
            </>
          )}
        </form>
      )}
    </div>
  );
}

// --- address book ------------------------------------------------------------------------------

export function AddressesPanel() {
  const toast = useToast();
  const [addresses, setAddresses] = useState<SavedAddress[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<SavedAddress | "new" | null>(null);
  const [deleting, setDeleting] = useState<SavedAddress | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setAddresses(await listAddresses());
      setError(null);
    } catch (e) {
      setError(message(e));
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads external data (API / session storage) on mount
    void load();
  }, [load]);

  async function confirmDelete() {
    if (!deleting) return;
    setBusy(true);
    try {
      await deleteAddress(deleting.id);
      toast.show({ title: "Address removed" });
      setDeleting(null);
      await load();
    } catch (e) {
      toast.show({ tone: "warning", title: "Couldn't remove the address", description: message(e) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className={styles.panel} aria-labelledby="addresses-title">
      <div className={styles.row} style={{ border: 0, padding: 0 }}>
        <h2 id="addresses-title" className={styles.panelTitle}>
          Saved addresses
        </h2>
        <Button size="sm" iconStart={<Plus aria-hidden="true" size={16} />} onClick={() => setEditing("new")} disabled={(addresses?.length ?? 0) >= 10}>
          Add address
        </Button>
      </div>
      {addresses === null && !error && <Loader variant="inline" label="Loading addresses…" />}
      {error && <EmptyState tone="error" title="We couldn't load your addresses" description={error} action={<Button onClick={() => void load()}>Try again</Button>} />}
      {addresses && addresses.length === 0 && <p className={styles.muted}>No saved addresses yet. Add one to check out faster.</p>}
      {addresses && addresses.length > 0 && (
        <ul className={styles.list}>
          {addresses.map((a) => (
            <li key={a.id} className={styles.row}>
              <div className={styles.rowMain}>
                <span className={styles.strong}>
                  {a.label || a.full_name}
                  {a.is_default && <span className={styles.muted}> · Default</span>}
                </span>
                <span className={styles.muted}>
                  {a.full_name}, {a.line1}
                  {a.line2 ? `, ${a.line2}` : ""}, {a.city}, {a.state} {a.postal_code} · {a.phone}
                </span>
              </div>
              <div className={styles.rowActions}>
                <Button size="sm" variant="ghost" iconStart={<Pencil aria-hidden="true" size={14} />} onClick={() => setEditing(a)} aria-label={`Edit address ${a.label || a.line1}`}>
                  Edit
                </Button>
                <Button size="sm" variant="ghost" iconStart={<Trash2 aria-hidden="true" size={14} />} onClick={() => setDeleting(a)} aria-label={`Remove address ${a.label || a.line1}`}>
                  Remove
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {editing && (
        <AddressDialog
          initial={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={async () => {
            setEditing(null);
            await load();
          }}
        />
      )}
      {deleting && (
        <Dialog
          open
          onClose={() => setDeleting(null)}
          title="Remove this address?"
          footer={
            <>
              <Button variant="ghost" onClick={() => setDeleting(null)}>
                Cancel
              </Button>
              <Button variant="accent" loading={busy} onClick={() => void confirmDelete()}>
                Remove
              </Button>
            </>
          }
        >
          <p className={styles.muted}>
            {deleting.line1}, {deleting.city} will be removed from your account. Past orders keep their own copy of the address.
          </p>
        </Dialog>
      )}
    </section>
  );
}

function AddressDialog({ initial, onClose, onSaved }: { initial: SavedAddress | null; onClose: () => void; onSaved: () => Promise<void> }) {
  const toast = useToast();
  const [address, setAddress] = useState<PostalAddress>(
    initial
      ? {
          full_name: initial.full_name,
          phone: initial.phone,
          line1: initial.line1,
          line2: initial.line2 ?? "",
          landmark: initial.landmark ?? "",
          city: initial.city,
          state: initial.state,
          postal_code: initial.postal_code,
        }
      : EMPTY_ADDRESS,
  );
  const [label, setLabel] = useState(initial?.label ?? "");
  const [isDefault, setIsDefault] = useState(initial?.is_default ?? false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const found = addressErrors(address);
    setErrors(found);
    if (Object.keys(found).length > 0 || busy) return;
    setBusy(true);
    const body = {
      ...address,
      line2: address.line2 || null,
      landmark: address.landmark || null,
      label: label.trim() || null,
      is_default: isDefault,
    };
    try {
      if (initial) await updateAddress(initial.id, body);
      else await addAddress(body);
      toast.show({ title: initial ? "Address updated" : "Address saved" });
      await onSaved();
    } catch (e) {
      toast.show({ tone: "warning", title: "Couldn't save the address", description: message(e) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open onClose={onClose} title={initial ? "Edit address" : "Add an address"}>
      <form className={styles.formStack} onSubmit={submit} noValidate>
        <TextField label="Label (optional, e.g. Home)" value={label} onChange={(e) => setLabel(e.target.value)} maxLength={40} />
        <AddressFields value={address} onChange={setAddress} errors={errors} />
        <label className={styles.lede} style={{ display: "inline-flex", gap: "var(--space-2)", alignItems: "center" }}>
          <input type="checkbox" checked={isDefault} onChange={(e) => setIsDefault(e.target.checked)} /> Use as my default address
        </label>
        <Button type="submit" loading={busy}>
          {initial ? "Save changes" : "Save address"}
        </Button>
      </form>
    </Dialog>
  );
}

// --- profile & password ------------------------------------------------------------------------

export function ProfilePanel({ user, onUpdated }: { user: CustomerProfile; onUpdated: (user: CustomerProfile) => void }) {
  const toast = useToast();
  const [name, setName] = useState(user.full_name);
  const [phone, setPhone] = useState(user.phone ?? "");
  const [saving, setSaving] = useState(false);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [passwordBusy, setPasswordBusy] = useState(false);
  const [passwordDone, setPasswordDone] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  async function saveProfile(event: FormEvent) {
    event.preventDefault();
    if (!name.trim() || saving) return;
    setSaving(true);
    try {
      onUpdated(await updateProfile({ fullName: name, phone }));
      toast.show({ title: "Profile updated" });
    } catch (e) {
      toast.show({ tone: "warning", title: "Couldn't update your profile", description: message(e) });
    } finally {
      setSaving(false);
    }
  }

  async function savePassword(event: FormEvent) {
    event.preventDefault();
    setPasswordError(null);
    setPasswordDone(false);
    if (next.length < 10) {
      setPasswordError("Your new password needs at least 10 characters.");
      return;
    }
    setPasswordBusy(true);
    try {
      await changePassword(current, next);
      setCurrent("");
      setNext("");
      setPasswordDone(true);
    } catch (e) {
      setPasswordError(message(e));
    } finally {
      setPasswordBusy(false);
    }
  }

  return (
    <div className={styles.formStack}>
      <section className={styles.panel} aria-labelledby="profile-title">
        <h2 id="profile-title" className={styles.panelTitle}>
          Profile
        </h2>
        <form className={styles.formStack} onSubmit={saveProfile}>
          <TextField label="Full name" value={name} onChange={(e) => setName(e.target.value)} required maxLength={120} autoComplete="name" />
          <TextField label="Mobile number (optional)" value={phone} onChange={(e) => setPhone(e.target.value)} type="tel" maxLength={20} autoComplete="tel" />
          <p className={styles.muted}>Email: {user.email}</p>
          <Button type="submit" loading={saving}>
            Save profile
          </Button>
        </form>
      </section>

      <section className={styles.panel} aria-labelledby="password-title">
        <h2 id="password-title" className={styles.panelTitle}>
          Change password
        </h2>
        <form className={styles.formStack} onSubmit={savePassword}>
          <TextField label="Current password" type="password" value={current} onChange={(e) => setCurrent(e.target.value)} required autoComplete="current-password" maxLength={128} />
          <TextField label="New password (10+ characters)" type="password" value={next} onChange={(e) => setNext(e.target.value)} required minLength={10} autoComplete="new-password" maxLength={128} />
          {passwordError && (
            <p className={styles.error} role="alert">
              {passwordError}
            </p>
          )}
          {passwordDone && (
            <p className={styles.success} role="status">
              Password changed. Other devices have been signed out.
            </p>
          )}
          <Button type="submit" loading={passwordBusy}>
            Change password
          </Button>
        </form>
      </section>
    </div>
  );
}
