"use client";

import Link from "next/link";
import { useState } from "react";

import { AdminPage, type Column, DataTable, ErrorState, LoadingState, Pill, adminStyles as styles } from "@/components/admin/Kit";
import { Button } from "@/components/ui/Button";
import { useResource } from "@/lib/admin/hooks";
import { WHATSAPP_STATUS_LABELS, type WhatsAppRequestSummary, ordersApi, whatsappTone } from "@/lib/admin/orders";
import { formatDateTime, formatMoney } from "@/lib/format";

export default function WhatsAppRequestsPage() {
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const list = useResource(() => ordersApi.whatsappList({ page, status, q: query }), JSON.stringify({ page, status, query }));

  const columns: Column<WhatsAppRequestSummary>[] = [
    {
      header: "Reference",
      render: (r) => (
        <Link href={`/admin/whatsapp/${r.id}`} className={styles.rowLink}>
          {r.reference}
        </Link>
      ),
    },
    { header: "Created", render: (r) => formatDateTime(r.created_at) },
    { header: "Customer", render: (r) => r.customer_name ?? <span className={styles.muted}>Not provided</span> },
    { header: "Status", render: (r) => <Pill tone={whatsappTone(r.status)}>{WHATSAPP_STATUS_LABELS[r.status]}</Pill> },
    { header: "Order", render: (r) => r.converted_order_number ?? "—" },
    { header: "Items", render: (r) => r.item_count, align: "end" },
    { header: "Estimate", render: (r) => formatMoney(r.estimated_subtotal), align: "end" },
  ];

  return (
    <AdminPage
      title="WhatsApp requests"
      description="A request is recorded when a customer is handed a WhatsApp link — that is not proof they sent it. Mark it once their message arrives, then convert it into an order after confirming availability and price."
    >
      <form
        className={styles.toolbar}
        role="search"
        onSubmit={(e) => {
          e.preventDefault();
          setQuery(search.trim());
          setPage(1);
        }}
      >
        <input className={styles.input} type="search" placeholder="Reference, name or phone" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search WhatsApp requests" maxLength={100} />
        <label className={styles.filter}>
          <span className="visually-hidden">Status</span>
          <select
            className={styles.select}
            value={status}
            aria-label="Status"
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All statuses</option>
            {Object.entries(WHATSAPP_STATUS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <Button type="submit" size="sm" variant="outline">
          Search
        </Button>
      </form>
      {list.error && <ErrorState message={list.error} onRetry={list.reload} />}
      {list.loading && !list.data && <LoadingState label="Loading WhatsApp requests…" />}
      {list.data && (
        <>
          <DataTable columns={columns} rows={list.data.items} rowKey={(r) => r.id} empty={<p className={styles.hint}>{query || status ? "No requests match these filters." : "No WhatsApp requests yet."}</p>} />
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
    </AdminPage>
  );
}
