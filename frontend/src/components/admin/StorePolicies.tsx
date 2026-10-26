"use client";

/** Settings cards for delivery coverage/messages and customer cancellation & return policy. */

import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/Button";
import { adminApi } from "@/lib/admin/api";
import { useMutation } from "@/lib/admin/hooks";
import { ORDER_STATUS_LABELS } from "@/lib/admin/orders";
import type { OrderPolicies, ShippingSettings, StoreSettings } from "@/lib/admin/types";
import { Card, CheckList, MoneyInput, SelectInput, TagInput, TextArea, TextInput, Toggle, adminStyles as styles } from "./Kit";

const MONEY = /^\d{1,10}(\.\d{1,2})?$/;
const PREFIX = /^[1-9]\d{0,5}$/;
const PIN = /^[1-9]\d{5}$/;

export function ShippingSettingsCard({ settings, onSaved }: { settings: StoreSettings; onSaved: (s: StoreSettings) => void }) {
  const initial = settings.shipping_settings ?? {};
  const [threshold, setThreshold] = useState(initial.free_shipping_threshold ?? "");
  const [mode, setMode] = useState<ShippingSettings["pin_mode"]>(initial.pin_mode ?? "all");
  const [prefixes, setPrefixes] = useState<string[]>(initial.allowed_pin_prefixes ?? []);
  const [blocked, setBlocked] = useState<string[]>(initial.blocked_pin_codes ?? []);
  const [message, setMessage] = useState(initial.shipping_message ?? "");
  const [estimate, setEstimate] = useState(initial.delivery_estimate ?? "");
  const [unserviceable, setUnserviceable] = useState(initial.unserviceable_message ?? "");
  const { run, pending } = useMutation();

  const errors: string[] = [];
  if (threshold && !MONEY.test(threshold)) errors.push("Free-shipping threshold must be an amount.");
  if (prefixes.some((p) => !PREFIX.test(p))) errors.push("PIN prefixes are 1–6 digits and can't start with 0.");
  if (blocked.some((p) => !PIN.test(p))) errors.push("Blocked PIN codes must be 6 digits.");
  if (mode === "allow_list" && prefixes.length === 0) errors.push("Add at least one PIN prefix, or deliver everywhere.");

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (errors.length) return;
    const body: ShippingSettings = {
      free_shipping_threshold: threshold || null,
      pin_mode: mode,
      allowed_pin_prefixes: mode === "allow_list" ? prefixes : [],
      blocked_pin_codes: blocked,
      shipping_message: message.trim(),
      delivery_estimate: estimate.trim(),
      unserviceable_message: unserviceable.trim(),
    };
    const res = await run(() => adminApi.updateSettings({ shipping_settings: body }), { success: "Delivery settings saved" });
    if (res.ok) onSaved(res.result);
  }

  return (
    <Card title="Delivery coverage & messages" hint="There's no courier integration — the delivery estimate is your own wording and is shown to customers as an estimate.">
      <form className={styles.stack} onSubmit={submit} noValidate>
        <MoneyInput label="Free shipping from (optional)" hint="Orders at or above this pay no shipping, whatever the rules say" value={threshold} onChange={setThreshold} />
        <SelectInput
          label="Where you deliver"
          value={mode}
          onChange={(v) => setMode(v as ShippingSettings["pin_mode"])}
          options={[
            { value: "all", label: "Everywhere in India" },
            { value: "allow_list", label: "Only PIN codes starting with…" },
          ]}
        />
        {mode === "allow_list" && (
          <TagInput label="Allowed PIN prefixes" hint="e.g. 4 for all of Maharashtra, or 4110 for part of Pune" values={prefixes} onChange={setPrefixes} max={500} maxLength={6} />
        )}
        <TagInput label="Blocked PIN codes (optional)" hint="Full 6-digit codes you can't deliver to" values={blocked} onChange={setBlocked} max={500} maxLength={6} />
        <TextInput label="Delivery estimate (optional)" placeholder="Your own estimate" value={estimate} onChange={setEstimate} maxLength={140} />
        <TextArea label="Shipping message (optional)" hint="Shown in the bag and at checkout" value={message} onChange={setMessage} rows={2} />
        <TextArea label="Message when a PIN code isn't covered (optional)" value={unserviceable} onChange={setUnserviceable} rows={2} />
        {errors.map((e) => (
          <p key={e} className={styles.errorText}>
            {e}
          </p>
        ))}
        <Button type="submit" loading={pending} disabled={errors.length > 0}>
          Save delivery settings
        </Button>
      </form>
    </Card>
  );
}

const CANCELLABLE = (["pending_confirmation", "confirmed", "processing", "packed"] as const).map((value) => ({
  value,
  label: ORDER_STATUS_LABELS[value],
}));

export function OrderPoliciesCard({ settings, onSaved }: { settings: StoreSettings; onSaved: (s: StoreSettings) => void }) {
  const initial = settings.order_policies ?? {};
  const [cancelOn, setCancelOn] = useState(initial.cancellation_enabled ?? false);
  const [statuses, setStatuses] = useState<string[]>(initial.cancellable_statuses ?? ["pending_confirmation", "confirmed"]);
  const [returnsOn, setReturnsOn] = useState(initial.returns_enabled ?? false);
  const [exchangesOn, setExchangesOn] = useState(initial.exchanges_enabled ?? false);
  const [windowDays, setWindowDays] = useState(String(initial.return_window_days ?? 7));
  const [reasons, setReasons] = useState<string[]>(initial.reasons ?? []);
  const [note, setNote] = useState(initial.policy_note ?? "");
  const { run, pending } = useMutation();

  const days = Number(windowDays);
  const errors: string[] = [];
  if (!Number.isInteger(days) || days < 0 || days > 90) errors.push("Return window must be 0–90 days.");
  if (cancelOn && statuses.length === 0) errors.push("Pick at least one status when cancellations are allowed.");
  if ((cancelOn || returnsOn || exchangesOn) && reasons.length === 0) errors.push("Add at least one reason customers can choose.");

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (errors.length) return;
    const body: OrderPolicies = {
      cancellation_enabled: cancelOn,
      cancellable_statuses: statuses,
      returns_enabled: returnsOn,
      exchanges_enabled: exchangesOn,
      return_window_days: days,
      reasons,
      policy_note: note.trim(),
    };
    const res = await run(() => adminApi.updateSettings({ order_policies: body }), { success: "Order policy saved" });
    if (res.ok) onSaved(res.result);
  }

  return (
    <Card
      title="Cancellations, returns & exchanges"
      hint="Controls what customers can request from their order history. Every request still needs your approval; refunds are never automatic."
    >
      <form className={styles.stack} onSubmit={submit} noValidate>
        <Toggle label="Customers can request a cancellation" checked={cancelOn} onChange={setCancelOn} />
        {cancelOn && <CheckList label="…while the order is" options={CANCELLABLE} selected={statuses} onChange={setStatuses} />}
        <Toggle label="Customers can request a return" checked={returnsOn} onChange={setReturnsOn} />
        <Toggle label="Customers can request an exchange" checked={exchangesOn} onChange={setExchangesOn} />
        {(returnsOn || exchangesOn) && (
          <TextInput
            label="Return / exchange window (days)"
            hint="Counted from the order date (no courier delivery date is available)"
            type="number"
            min={0}
            max={90}
            value={windowDays}
            onChange={setWindowDays}
          />
        )}
        <TagInput label="Reasons customers can pick" values={reasons} onChange={setReasons} max={12} maxLength={40} />
        <TextArea label="Policy note shown with the request form (optional)" value={note} onChange={setNote} rows={2} />
        {errors.map((e) => (
          <p key={e} className={styles.errorText}>
            {e}
          </p>
        ))}
        <Button type="submit" loading={pending} disabled={errors.length > 0}>
          Save order policy
        </Button>
      </form>
    </Card>
  );
}
