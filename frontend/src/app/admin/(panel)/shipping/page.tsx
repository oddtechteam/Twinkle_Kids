"use client";

import { Pencil, Plus, Trash2 } from "lucide-react";
import { type FormEvent, useState } from "react";

import {
  AdminPage,
  type Column,
  ConfirmDialog,
  DataTable,
  ErrorState,
  LoadingState,
  MoneyInput,
  Pill,
  TextInput,
  Toggle,
  adminStyles as styles,
} from "@/components/admin/Kit";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { adminApi } from "@/lib/admin/api";
import { useMutation, useResource } from "@/lib/admin/hooks";
import type { ShippingRule } from "@/lib/admin/types";
import { formatMoney } from "@/lib/format";

const MONEY = /^\d{1,10}(\.\d{1,2})?$/;

function RuleDialog({ rule, onClose, onSaved }: { rule: ShippingRule | null; onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState(rule?.name ?? "");
  const [fee, setFee] = useState(rule?.fee ?? "");
  const [min, setMin] = useState(rule?.min_order_amount ?? "0");
  const [max, setMax] = useState(rule?.max_order_amount ?? "");
  const [priority, setPriority] = useState(String(rule?.priority ?? 100));
  const [active, setActive] = useState(rule?.is_active ?? true);
  const { run, pending } = useMutation();

  const valid = name.trim() && MONEY.test(fee) && MONEY.test(min || "0") && (!max || MONEY.test(max)) && (!max || Number(max) >= Number(min || 0));

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!valid) return;
    const body = {
      name: name.trim(),
      fee,
      min_order_amount: min || "0",
      max_order_amount: max || null,
      priority: Number.parseInt(priority || "100", 10),
      is_active: active,
    };
    const res = await run(() => (rule ? adminApi.updateShippingRule(rule.id, body) : adminApi.createShippingRule(body)), {
      success: rule ? "Shipping rule saved" : "Shipping rule added",
    });
    if (res.ok) onSaved();
  };

  return (
    <Dialog open onClose={onClose} title={rule ? "Edit shipping rule" : "New shipping rule"}>
      <form onSubmit={submit} className={styles.stack} noValidate>
        <TextInput label="Name" placeholder="e.g. Free shipping over ₹999" value={name} onChange={setName} maxLength={80} required />
        <MoneyInput label="Shipping fee" hint="Use 0 for free shipping" value={fee} onChange={setFee} required />
        <div className={styles.grid2}>
          <MoneyInput label="Applies from order value" value={min} onChange={setMin} />
          <MoneyInput label="Up to order value" hint="Empty = no upper limit" value={max} onChange={setMax} />
        </div>
        <TextInput label="Priority" type="number" min={0} hint="Lower numbers are checked first" value={priority} onChange={setPriority} />
        <Toggle label="Active" checked={active} onChange={setActive} />
        {max && MONEY.test(max) && Number(max) < Number(min || 0) && <p className={styles.errorText}>The upper limit must be at least the starting value.</p>}
        <Button type="submit" loading={pending} disabled={!valid}>
          {rule ? "Save rule" : "Add rule"}
        </Button>
      </form>
    </Dialog>
  );
}

export default function ShippingRulesPage() {
  const rules = useResource(adminApi.shippingRules, "shipping");
  const { run, pending } = useMutation();
  const [editing, setEditing] = useState<ShippingRule | null | "new">(null);
  const [deleting, setDeleting] = useState<ShippingRule | null>(null);

  const columns: Column<ShippingRule>[] = [
    { header: "Rule", render: (r) => <strong>{r.name}</strong> },
    { header: "Fee", render: (r) => (Number(r.fee) === 0 ? "Free" : formatMoney(r.fee)) },
    {
      header: "Order value",
      render: (r) => `${formatMoney(r.min_order_amount)} – ${r.max_order_amount ? formatMoney(r.max_order_amount) : "no limit"}`,
    },
    { header: "Priority", render: (r) => r.priority },
    { header: "Status", render: (r) => (r.is_active ? <Pill tone="green">Active</Pill> : <Pill tone="grey">Off</Pill>) },
    {
      header: "Actions",
      align: "end",
      render: (r) => (
        <div className={styles.rowActions}>
          <button type="button" className={styles.iconButton} onClick={() => setEditing(r)} aria-label={`Edit ${r.name}`}>
            <Pencil size={15} aria-hidden="true" />
          </button>
          <button type="button" className={`${styles.iconButton} ${styles.dangerIcon}`} onClick={() => setDeleting(r)} aria-label={`Delete ${r.name}`}>
            <Trash2 size={15} aria-hidden="true" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <AdminPage
      title="Shipping rules"
      description="Fees by order value. Rules are listed in priority order."
      breadcrumbs={[{ label: "Shipping" }]}
      actions={
        <Button iconStart={<Plus aria-hidden="true" />} onClick={() => setEditing("new")}>
          New rule
        </Button>
      }
    >
      {rules.error && <ErrorState message={rules.error} onRetry={rules.reload} />}
      {rules.loading && !rules.data && <LoadingState label="Loading shipping rules…" />}
      {rules.data && <DataTable columns={columns} rows={rules.data} rowKey={(r) => r.id} empty={<p className={styles.hint}>No shipping rules yet.</p>} />}
      {editing !== null && (
        <RuleDialog
          key={editing === "new" ? "new" : editing.id}
          rule={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            void rules.reload();
          }}
        />
      )}
      <ConfirmDialog
        open={deleting !== null}
        title={`Delete “${deleting?.name ?? ""}”?`}
        message="Existing orders keep the shipping fee they were placed with."
        confirmLabel="Delete rule"
        destructive
        pending={pending}
        onClose={() => setDeleting(null)}
        onConfirm={async () => {
          if (!deleting) return;
          const res = await run(() => adminApi.deleteShippingRule(deleting.id), { success: "Shipping rule deleted" });
          setDeleting(null);
          if (res.ok) void rules.reload();
        }}
      />
    </AdminPage>
  );
}
