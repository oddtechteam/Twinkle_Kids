"use client";

import Link from "next/link";
import { useState } from "react";

import {
  AdminPage,
  type Column,
  ConfirmDialog,
  DataTable,
  ErrorState,
  LoadingState,
  MoneyInput,
  Pill,
  TextArea,
  Toggle,
  adminStyles as styles,
} from "@/components/admin/Kit";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { useMutation, useResource } from "@/lib/admin/hooks";
import { type OrderRequest, REQUEST_STATUS_LABELS, type RequestStatus, opsApi } from "@/lib/admin/operations";
import { formatDateTime, formatMoney } from "@/lib/format";

const KIND_LABELS = { cancellation: "Cancellation", return: "Return", exchange: "Exchange" } as const;
const tone = (s: RequestStatus) => (s === "completed" ? "green" : s === "rejected" ? "grey" : "amber");

export default function RequestsPage() {
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("requested");
  const [kind, setKind] = useState("");
  const [open, setOpen] = useState<OrderRequest | null>(null);
  const list = useResource(() => opsApi.requests({ page, status, kind }), JSON.stringify({ page, status, kind }));

  const columns: Column<OrderRequest>[] = [
    {
      header: "Request",
      render: (r) => (
        <button type="button" className={styles.rowLink} onClick={() => setOpen(r)}>
          {r.reference}
        </button>
      ),
    },
    { header: "Type", render: (r) => KIND_LABELS[r.kind] },
    {
      header: "Order",
      render: (r) => (
        <Link href={`/admin/orders/${r.order_id}`} className={styles.rowLink}>
          {r.order_number}
        </Link>
      ),
    },
    { header: "Reason", render: (r) => r.reason },
    { header: "Raised", render: (r) => formatDateTime(r.created_at) },
    { header: "Status", render: (r) => <Pill tone={tone(r.status)}>{REQUEST_STATUS_LABELS[r.status]}</Pill> },
  ];

  const filter = (label: string, value: string, onChange: (v: string) => void, options: [string, string][]) => (
    <label className={styles.filter}>
      <span className="visually-hidden">{label}</span>
      <select
        className={styles.select}
        aria-label={label}
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          setPage(1);
        }}
      >
        {options.map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
    </label>
  );

  return (
    <AdminPage
      title="Cancellations & returns"
      description="Customer requests under your order policy. Refunds are never automatic — record what you actually refunded. Stock is added back only when returned goods are received and checked."
    >
      <div className={styles.toolbar}>
        {filter("Status", status, setStatus, [["", "All statuses"], ...(Object.entries(REQUEST_STATUS_LABELS) as [string, string][])])}
        {filter("Type", kind, setKind, [["", "All types"], ["cancellation", "Cancellations"], ["return", "Returns"], ["exchange", "Exchanges"]])}
      </div>
      {list.error && <ErrorState message={list.error} onRetry={list.reload} />}
      {list.loading && !list.data && <LoadingState label="Loading requests…" />}
      {list.data && (
        <>
          <DataTable columns={columns} rows={list.data.items} rowKey={(r) => r.id} empty={<p className={styles.hint}>No requests here.</p>} />
          {list.data.pages > 1 && (
            <div className={styles.pager}>
              <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                Previous
              </Button>
              <span className={styles.hint}>
                Page {list.data.page} of {list.data.pages}
              </span>
              <Button size="sm" variant="outline" disabled={page >= list.data.pages} onClick={() => setPage(page + 1)}>
                Next
              </Button>
            </div>
          )}
        </>
      )}
      {open && (
        <RequestDialog
          request={open}
          onClose={() => setOpen(null)}
          onChanged={(updated) => {
            setOpen(updated);
            void list.reload();
          }}
        />
      )}
    </AdminPage>
  );
}

function RequestDialog({ request, onClose, onChanged }: { request: OrderRequest; onClose: () => void; onChanged: (r: OrderRequest) => void }) {
  const { run, pending } = useMutation();
  const [note, setNote] = useState("");
  const [restock, setRestock] = useState(true);
  const [refund, setRefund] = useState("");
  const [confirm, setConfirm] = useState<"approve" | "reject" | "received" | "complete" | null>(null);
  const r = request;
  const goods = r.kind !== "cancellation";

  async function act() {
    const text = note.trim() || null;
    const action =
      confirm === "approve" || confirm === "reject"
        ? () => opsApi.decide(r.id, confirm === "approve", text)
        : confirm === "received"
          ? () => opsApi.received(r.id, restock, text)
          : () => opsApi.complete(r.id, refund || null, text);
    const res = await run(action, { success: "Request updated" });
    setConfirm(null);
    if (res.ok) {
      setNote("");
      onChanged(res.result);
    }
  }

  const messages: Record<NonNullable<typeof confirm>, string> = {
    approve:
      r.kind === "cancellation"
        ? "This cancels the order and puts its stock back. No refund is made automatically."
        : `Approve this ${r.kind}. Stock changes only when you record the goods as received.`,
    reject: "The customer will see that the request was declined, with your note.",
    received: restock ? "The returned items will be added back to stock (only if they're resellable)." : "The goods are recorded as received without restocking.",
    complete: refund ? `Record a refund of ${formatMoney(refund)} that you've made outside this system.` : "Close the request without a refund.",
  };

  return (
    <Dialog open onClose={onClose} title={`${KIND_LABELS[r.kind]} request ${r.reference}`}>
      <div className={styles.stack}>
        <dl className={styles.kv}>
          <dt>Order</dt>
          <dd>
            <Link href={`/admin/orders/${r.order_id}`} className={styles.rowLink}>
              {r.order_number}
            </Link>
          </dd>
          <dt>Status</dt>
          <dd>{REQUEST_STATUS_LABELS[r.status]}</dd>
          <dt>Reason</dt>
          <dd>{r.reason}</dd>
          {r.customer_message && (
            <>
              <dt>Customer says</dt>
              <dd>{r.customer_message}</dd>
            </>
          )}
          {r.items.length > 0 && (
            <>
              <dt>Items</dt>
              <dd>{r.items.map((i) => `${i.sku} × ${i.quantity}`).join(", ")}</dd>
            </>
          )}
          {r.resolution_note && (
            <>
              <dt>Resolution</dt>
              <dd>{r.resolution_note}</dd>
            </>
          )}
          {r.refund_amount && (
            <>
              <dt>Refund recorded</dt>
              <dd>{formatMoney(r.refund_amount)}</dd>
            </>
          )}
          {goods && (
            <>
              <dt>Restocked</dt>
              <dd>{r.restocked ? "Yes" : "No"}</dd>
            </>
          )}
        </dl>

        {r.status !== "completed" && r.status !== "rejected" && (
          <TextArea label="Note for the record (shown to the customer)" value={note} onChange={setNote} maxLength={1000} rows={2} />
        )}
        {r.status === "requested" && (
          <div className={styles.rowActions}>
            <Button onClick={() => setConfirm("approve")}>Approve</Button>
            <Button variant="outline" onClick={() => setConfirm("reject")}>
              Reject
            </Button>
          </div>
        )}
        {r.status === "approved" && goods && (
          <div className={styles.stack}>
            <Toggle label="Items checked and resellable — add back to stock" checked={restock} onChange={setRestock} />
            <Button onClick={() => setConfirm("received")}>Record goods received</Button>
          </div>
        )}
        {(r.status === "approved" || r.status === "received") && (
          <div className={styles.stack}>
            <MoneyInput label="Refund you made (optional)" value={refund} onChange={setRefund} />
            <Button variant="outline" onClick={() => setConfirm("complete")}>
              Complete request
            </Button>
          </div>
        )}
      </div>
      <ConfirmDialog
        open={confirm !== null}
        title="Confirm"
        message={confirm ? messages[confirm] : ""}
        confirmLabel="Confirm"
        destructive={confirm === "reject"}
        pending={pending}
        onConfirm={() => void act()}
        onClose={() => setConfirm(null)}
      />
    </Dialog>
  );
}
