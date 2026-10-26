"use client";

import { Pencil, Plus } from "lucide-react";
import { type FormEvent, useState } from "react";

import {
  AdminPage,
  CheckList,
  type Column,
  DataTable,
  ErrorState,
  LoadingState,
  MoneyInput,
  Pill,
  SelectInput,
  TextInput,
  Toggle,
  adminStyles as styles,
} from "@/components/admin/Kit";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { adminApi } from "@/lib/admin/api";
import { useMutation, useResource } from "@/lib/admin/hooks";
import { type Coupon, type CouponBody, opsApi } from "@/lib/admin/operations";
import { formatDateTime, formatMoney } from "@/lib/format";

const MONEY = /^\d{1,10}(\.\d{1,2})?$/;
const CODE = /^[A-Z0-9][A-Z0-9_-]{2,39}$/;

function describe(c: Coupon): string {
  const value = c.discount_type === "percentage" ? `${Number(c.discount_value)}% off` : `${formatMoney(c.discount_value)} off`;
  const scope = c.category_ids.length || c.collection_ids.length || c.product_ids.length ? " selected items" : " the order";
  return `${value}${scope}`;
}

function windowLabel(c: Coupon): string {
  const now = Date.now();
  if (c.ends_at && Date.parse(c.ends_at) <= now) return "Expired";
  if (c.starts_at && Date.parse(c.starts_at) > now) return `Starts ${formatDateTime(c.starts_at)}`;
  return c.ends_at ? `Until ${formatDateTime(c.ends_at)}` : "No end date";
}

export default function CouponsPage() {
  const list = useResource(() => opsApi.coupons(), "coupons");
  const { run, pending } = useMutation();
  const [editing, setEditing] = useState<Coupon | "new" | null>(null);

  const columns: Column<Coupon>[] = [
    { header: "Code", render: (c) => <span className={styles.mono}>{c.code}</span> },
    { header: "Discount", render: (c) => describe(c) },
    { header: "Window", render: (c) => windowLabel(c) },
    {
      header: "Used",
      render: (c) => `${c.times_used}${c.usage_limit ? ` / ${c.usage_limit}` : ""}`,
      align: "end",
    },
    { header: "Discount given", render: (c) => formatMoney(c.discount_given), align: "end" },
    { header: "State", render: (c) => <Pill tone={c.is_active ? "green" : "grey"}>{c.is_active ? "Active" : "Paused"}</Pill> },
    {
      header: "",
      render: (c) => (
        <div className={styles.rowActions}>
          <Button size="sm" variant="ghost" iconStart={<Pencil aria-hidden="true" size={14} />} onClick={() => setEditing(c)}>
            Edit
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={pending}
            onClick={async () => {
              const res = await run(() => opsApi.setCouponActive(c.id, !c.is_active), { success: c.is_active ? `${c.code} paused` : `${c.code} activated` });
              if (res.ok) void list.reload();
            }}
          >
            {c.is_active ? "Pause" : "Activate"}
          </Button>
        </div>
      ),
    },
  ];

  return (
    <AdminPage
      title="Coupons"
      description="Codes are always re-checked on the server at checkout. A discount never exceeds the eligible items' price and never touches the original-price rules."
      actions={
        <Button iconStart={<Plus aria-hidden="true" />} onClick={() => setEditing("new")}>
          New coupon
        </Button>
      }
    >
      {list.error && <ErrorState message={list.error} onRetry={list.reload} />}
      {list.loading && !list.data && <LoadingState label="Loading coupons…" />}
      {list.data && <DataTable columns={columns} rows={list.data} rowKey={(c) => c.id} empty={<p className={styles.hint}>No coupons yet.</p>} />}
      {editing && (
        <CouponDialog
          coupon={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            void list.reload();
          }}
        />
      )}
    </AdminPage>
  );
}

const toLocal = (iso: string | null) => (iso ? iso.slice(0, 16) : "");
const fromLocal = (value: string) => (value ? new Date(value).toISOString() : null);

function CouponDialog({ coupon, onClose, onSaved }: { coupon: Coupon | null; onClose: () => void; onSaved: () => void }) {
  const { run, pending } = useMutation();
  const categories = useResource(() => adminApi.categories(), "coupon-cats");
  const collections = useResource(() => adminApi.collections(), "coupon-cols");
  const [code, setCode] = useState(coupon?.code ?? "");
  const [description, setDescription] = useState(coupon?.description ?? "");
  const [type, setType] = useState<Coupon["discount_type"]>(coupon?.discount_type ?? "percentage");
  const [value, setValue] = useState(coupon?.discount_value ?? "");
  const [minOrder, setMinOrder] = useState(coupon?.min_order_amount ?? "");
  const [maxDiscount, setMaxDiscount] = useState(coupon?.max_discount_amount ?? "");
  const [startsAt, setStartsAt] = useState(toLocal(coupon?.starts_at ?? null));
  const [endsAt, setEndsAt] = useState(toLocal(coupon?.ends_at ?? null));
  const [usageLimit, setUsageLimit] = useState(coupon?.usage_limit ? String(coupon.usage_limit) : "");
  const [perUser, setPerUser] = useState(coupon?.per_user_limit ? String(coupon.per_user_limit) : "");
  const [active, setActive] = useState(coupon?.is_active ?? true);
  const [categoryIds, setCategoryIds] = useState<string[]>(coupon?.category_ids ?? []);
  const [collectionIds, setCollectionIds] = useState<string[]>(coupon?.collection_ids ?? []);

  const upper = code.trim().toUpperCase();
  const errors: Record<string, string> = {};
  if (!CODE.test(upper)) errors.code = "3–40 characters: letters, numbers, - or _.";
  if (!MONEY.test(value) || Number(value) <= 0) errors.value = "Enter an amount above zero.";
  else if (type === "percentage" && Number(value) > 100) errors.value = "Percentages can't exceed 100.";
  if (minOrder && !MONEY.test(minOrder)) errors.minOrder = "Enter a valid amount.";
  if (maxDiscount && (!MONEY.test(maxDiscount) || Number(maxDiscount) <= 0)) errors.maxDiscount = "Enter an amount above zero.";
  if (startsAt && endsAt && endsAt <= startsAt) errors.endsAt = "End must be after the start.";
  if (usageLimit && !(Number(usageLimit) >= 1)) errors.usage = "At least 1.";
  if (perUser && !(Number(perUser) >= 1)) errors.perUser = "At least 1.";
  const valid = Object.keys(errors).length === 0;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!valid) return;
    const body: CouponBody = {
      code: upper,
      description: description.trim() || null,
      discount_type: type,
      discount_value: value,
      is_active: active,
      min_order_amount: minOrder || null,
      max_discount_amount: type === "percentage" ? maxDiscount || null : null,
      starts_at: fromLocal(startsAt),
      ends_at: fromLocal(endsAt),
      usage_limit: usageLimit ? Number(usageLimit) : null,
      per_user_limit: perUser ? Number(perUser) : null,
      product_ids: coupon?.product_ids ?? [],
      category_ids: categoryIds,
      collection_ids: collectionIds,
    };
    const res = await run(() => (coupon ? opsApi.updateCoupon(coupon.id, body) : opsApi.createCoupon(body)), {
      success: coupon ? "Coupon saved" : "Coupon created",
    });
    if (res.ok) onSaved();
  }

  return (
    <Dialog open onClose={onClose} title={coupon ? `Edit ${coupon.code}` : "New coupon"}>
      <form className={styles.stack} onSubmit={submit} noValidate>
        <div className={styles.grid2}>
          <TextInput label="Code" value={code} onChange={setCode} error={code ? errors.code : null} required maxLength={40} />
          <SelectInput
            label="Discount type"
            value={type}
            onChange={(v) => setType(v as Coupon["discount_type"])}
            options={[
              { value: "percentage", label: "Percentage off" },
              { value: "fixed_amount", label: "Fixed amount off" },
            ]}
          />
          {type === "percentage" ? (
            <TextInput label="Percent" value={value} onChange={setValue} error={value ? errors.value : null} inputMode="decimal" required />
          ) : (
            <MoneyInput label="Amount" value={value} onChange={setValue} required />
          )}
          {type === "percentage" && <MoneyInput label="Maximum discount (optional)" value={maxDiscount} onChange={setMaxDiscount} />}
          <MoneyInput label="Minimum order (optional)" value={minOrder} onChange={setMinOrder} />
          <TextInput label="Total uses allowed (optional)" value={usageLimit} onChange={setUsageLimit} inputMode="numeric" error={errors.usage} />
          <TextInput label="Uses per customer (optional)" hint="Customers must be signed in" value={perUser} onChange={setPerUser} inputMode="numeric" error={errors.perUser} />
          <TextInput label="Starts (optional)" type="datetime-local" value={startsAt} onChange={setStartsAt} />
          <TextInput label="Ends (optional)" type="datetime-local" value={endsAt} onChange={setEndsAt} error={errors.endsAt} />
        </div>
        <TextInput label="Internal description (optional)" value={description} onChange={setDescription} maxLength={255} />
        {categories.data && categories.data.length > 0 && (
          <CheckList
            label="Only for these categories (optional)"
            options={categories.data.map((c) => ({ value: c.id, label: c.name }))}
            selected={categoryIds}
            onChange={setCategoryIds}
          />
        )}
        {collections.data && collections.data.length > 0 && (
          <CheckList
            label="Only for these collections (optional)"
            options={collections.data.map((c) => ({ value: c.id, label: c.name }))}
            selected={collectionIds}
            onChange={setCollectionIds}
          />
        )}
        <p className={styles.hint}>Leave both empty for a whole-order discount. With a selection, only matching items are discounted.</p>
        <Toggle label="Active" checked={active} onChange={setActive} />
        <Button type="submit" loading={pending} disabled={!valid}>
          {coupon ? "Save coupon" : "Create coupon"}
        </Button>
      </form>
    </Dialog>
  );
}
