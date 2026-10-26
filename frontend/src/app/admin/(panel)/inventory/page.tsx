"use client";

import Link from "next/link";
import { History, SlidersHorizontal } from "lucide-react";
import { type FormEvent, useState } from "react";

import {
  AdminPage,
  type Column,
  DataTable,
  ErrorState,
  LoadingState,
  Pill,
  SelectInput,
  TextArea,
  TextInput,
  adminStyles as styles,
} from "@/components/admin/Kit";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { useMutation, useResource } from "@/lib/admin/hooks";
import {
  type AdjustReason,
  type InventoryRow,
  MOVEMENT_LABELS,
  STOCK_STATE_LABELS,
  opsApi,
} from "@/lib/admin/operations";
import { formatDateTime } from "@/lib/format";

const TONE = { in_stock: "green", low_stock: "amber", out_of_stock: "red", untracked: "grey" } as const;

export default function InventoryPage() {
  const [page, setPage] = useState(1);
  const [state, setState] = useState("");
  const [search, setSearch] = useState("");
  const [term, setTerm] = useState("");
  const [adjusting, setAdjusting] = useState<InventoryRow | null>(null);
  const [history, setHistory] = useState<InventoryRow | null>(null);
  const list = useResource(() => opsApi.inventory({ page, state, q: term }), JSON.stringify({ page, state, term }));

  const columns: Column<InventoryRow>[] = [
    {
      header: "Product",
      render: (r) => (
        <>
          <Link href={`/admin/products/${r.product_id}`} className={styles.rowLink}>
            {r.product_name}
          </Link>
          <span className={styles.muted}> {[r.size, r.colour].filter(Boolean).join(" · ")}</span>
          {!r.is_active && <span className={styles.muted}> (option hidden)</span>}
        </>
      ),
    },
    { header: "SKU", render: (r) => <span className={styles.mono}>{r.sku}</span> },
    { header: "Status", render: (r) => <Pill tone={TONE[r.state]}>{STOCK_STATE_LABELS[r.state]}</Pill> },
    { header: "Available", render: (r) => (r.track_inventory ? r.stock_quantity : "—"), align: "end" },
    { header: "Low at", render: (r) => r.low_stock_threshold, align: "end" },
    {
      header: "",
      render: (r) => (
        <div className={styles.rowActions}>
          <Button size="sm" variant="soft" iconStart={<SlidersHorizontal aria-hidden="true" size={14} />} onClick={() => setAdjusting(r)} disabled={!r.track_inventory}>
            Adjust
          </Button>
          <Button size="sm" variant="ghost" iconStart={<History aria-hidden="true" size={14} />} onClick={() => setHistory(r)} aria-label={`Stock history for ${r.sku}`}>
            History
          </Button>
        </div>
      ),
    },
  ];

  return (
    <AdminPage
      title="Inventory"
      description="Available stock per variant. Orders deduct stock when placed; cancellations put it back; returns only after the goods are received and verified. WhatsApp requests never change stock."
    >
      <form
        className={styles.toolbar}
        role="search"
        onSubmit={(e) => {
          e.preventDefault();
          setTerm(search.trim());
          setPage(1);
        }}
      >
        <input className={styles.input} type="search" placeholder="Product name or SKU" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search inventory" maxLength={100} />
        <label className={styles.filter}>
          <span className="visually-hidden">Stock status</span>
          <select
            className={styles.select}
            value={state}
            aria-label="Stock status"
            onChange={(e) => {
              setState(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All stock levels</option>
            <option value="out_of_stock">Out of stock</option>
            <option value="low_stock">Low stock</option>
            <option value="in_stock">In stock</option>
          </select>
        </label>
        <Button type="submit" size="sm" variant="outline">
          Search
        </Button>
      </form>
      {list.error && <ErrorState message={list.error} onRetry={list.reload} />}
      {list.loading && !list.data && <LoadingState label="Loading inventory…" />}
      {list.data && (
        <>
          <DataTable columns={columns} rows={list.data.items} rowKey={(r) => r.variant_id} empty={<p className={styles.hint}>{term || state ? "No variants match these filters." : "No products yet."}</p>} />
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
      {adjusting && (
        <AdjustDialog
          row={adjusting}
          onClose={() => setAdjusting(null)}
          onSaved={() => {
            setAdjusting(null);
            void list.reload();
          }}
        />
      )}
      {history && <HistoryDialog row={history} onClose={() => setHistory(null)} />}
    </AdminPage>
  );
}

function AdjustDialog({ row, onClose, onSaved }: { row: InventoryRow; onClose: () => void; onSaved: () => void }) {
  const { run, pending } = useMutation();
  const [reason, setReason] = useState<AdjustReason>("restock");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const qty = Number.parseInt(amount, 10);
  const removes = reason === "damaged" || (reason === "adjustment" && amount.trim().startsWith("-"));
  const delta = Number.isFinite(qty) ? (reason === "damaged" ? -Math.abs(qty) : reason === "restock" || reason === "return" ? Math.abs(qty) : qty) : 0;
  const after = row.stock_quantity + delta;
  const valid = delta !== 0 && after >= 0;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!valid) return;
    const res = await run(() => opsApi.adjustStock(row.variant_id, { delta, reason, note: note.trim() || null }), {
      success: `Stock for ${row.sku} is now ${after}`,
    });
    if (res.ok) onSaved();
  }

  return (
    <Dialog open onClose={onClose} title={`Adjust stock · ${row.sku}`}>
      <form className={styles.stack} onSubmit={submit} noValidate>
        <p className={styles.hint}>
          {row.product_name} {[row.size, row.colour].filter(Boolean).join(" · ")} — currently <strong>{row.stock_quantity}</strong> available.
        </p>
        <SelectInput
          label="Reason"
          value={reason}
          onChange={(v) => setReason(v as AdjustReason)}
          options={[
            { value: "restock", label: "Restock (adds stock)" },
            { value: "return", label: "Return received outside a request (adds stock)" },
            { value: "damaged", label: "Damaged or lost (removes stock)" },
            { value: "adjustment", label: "Stock-count correction (+ or −)" },
          ]}
        />
        <TextInput
          label={reason === "adjustment" ? "Change (use − to remove)" : "Quantity"}
          value={amount}
          onChange={setAmount}
          inputMode="numeric"
          error={amount && !valid ? (after < 0 ? "Stock can't go below zero." : "Enter a non-zero amount.") : null}
          hint={valid ? `Stock after: ${after}${removes ? " (removing)" : ""}` : undefined}
          required
        />
        <TextArea label="Note (optional)" value={note} onChange={setNote} maxLength={500} rows={2} />
        <Button type="submit" loading={pending} disabled={!valid}>
          Record adjustment
        </Button>
      </form>
    </Dialog>
  );
}

function HistoryDialog({ row, onClose }: { row: InventoryRow; onClose: () => void }) {
  const moves = useResource(() => opsApi.movements({ variant_id: row.variant_id }), row.variant_id);
  return (
    <Dialog open onClose={onClose} title={`Stock history · ${row.sku}`}>
      {moves.loading && !moves.data && <LoadingState inline label="Loading history…" />}
      {moves.error && <ErrorState message={moves.error} onRetry={moves.reload} />}
      {moves.data && moves.data.items.length === 0 && <p className={styles.hint}>No stock movements yet.</p>}
      {moves.data && moves.data.items.length > 0 && (
        <ul className={styles.list}>
          {moves.data.items.map((m) => (
            <li key={m.id} className={styles.listRow} style={{ display: "grid", gap: "2px" }}>
              <span>
                <strong>{m.quantity_delta > 0 ? `+${m.quantity_delta}` : m.quantity_delta}</strong> · {MOVEMENT_LABELS[m.reason] ?? m.reason} → {m.stock_after}
              </span>
              <span className={styles.muted}>
                {formatDateTime(m.created_at)}
                {m.order_number && ` · order ${m.order_number}`}
                {m.actor_email && ` · ${m.actor_email}`}
                {m.note && ` · ${m.note}`}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Dialog>
  );
}
