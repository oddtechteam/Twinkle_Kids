"use client";

import Link from "next/link";
import { useState } from "react";

import { AdminPage, type Column, DataTable, ErrorState, LoadingState, Pill, adminStyles as styles } from "@/components/admin/Kit";
import { Button } from "@/components/ui/Button";
import { useResource } from "@/lib/admin/hooks";
import { type AdminOrderSummary, ORDER_STATUS_LABELS, PAYMENT_STATUS_LABELS, ordersApi, paymentTone, statusTone } from "@/lib/admin/orders";
import { formatDateTime, formatMoney } from "@/lib/format";

export default function OrdersPage() {
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [source, setSource] = useState("");
  const [payment, setPayment] = useState("");
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const key = JSON.stringify({ page, status, source, payment, query });
  const list = useResource(() => ordersApi.list({ page, status, source, payment_status: payment, q: query }), key);

  const columns: Column<AdminOrderSummary>[] = [
    {
      header: "Order",
      render: (o) => (
        <Link href={`/admin/orders/${o.id}`} className={styles.rowLink}>
          {o.order_number}
        </Link>
      ),
    },
    { header: "Placed", render: (o) => formatDateTime(o.placed_at) },
    { header: "Customer", render: (o) => o.customer_name },
    { header: "Source", render: (o) => <Pill tone={o.source === "whatsapp" ? "green" : "grey"}>{o.source === "whatsapp" ? "WhatsApp" : "Website"}</Pill> },
    { header: "Status", render: (o) => <Pill tone={statusTone(o.status)}>{ORDER_STATUS_LABELS[o.status]}</Pill> },
    { header: "Payment", render: (o) => <Pill tone={paymentTone(o.payment_status)}>{PAYMENT_STATUS_LABELS[o.payment_status]}</Pill> },
    { header: "Items", render: (o) => o.item_count, align: "end" },
    { header: "Order total", render: (o) => formatMoney(o.grand_total), align: "end" },
  ];

  const select = (label: string, value: string, onChange: (v: string) => void, options: [string, string][]) => (
    <label className={styles.filter}>
      <span className="visually-hidden">{label}</span>
      <select
        className={styles.select}
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          setPage(1);
        }}
        aria-label={label}
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
    <AdminPage title="Orders" description="Website orders and confirmed WhatsApp orders. Order totals are not revenue until a payment is recorded.">
      <form
        className={styles.toolbar}
        onSubmit={(e) => {
          e.preventDefault();
          setQuery(search.trim());
          setPage(1);
        }}
        role="search"
      >
        <input className={styles.input} type="search" placeholder="Order no., name, email or phone" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search orders" maxLength={100} />
        {select("Status", status, setStatus, [["", "All statuses"], ...(Object.entries(ORDER_STATUS_LABELS) as [string, string][])])}
        {select("Source", source, setSource, [["", "All sources"], ["website", "Website"], ["whatsapp", "WhatsApp"]])}
        {select("Payment", payment, setPayment, [["", "All payments"], ...(Object.entries(PAYMENT_STATUS_LABELS) as [string, string][])])}
        <Button type="submit" size="sm" variant="outline">
          Search
        </Button>
      </form>
      {list.error && <ErrorState message={list.error} onRetry={list.reload} />}
      {list.loading && !list.data && <LoadingState label="Loading orders…" />}
      {list.data && (
        <>
          <DataTable columns={columns} rows={list.data.items} rowKey={(o) => o.id} empty={<p className={styles.hint}>{query || status || source || payment ? "No orders match these filters." : "No orders yet."}</p>} />
          {list.data.pages > 1 && (
            <div className={styles.pager}>
              <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                Previous
              </Button>
              <span className={styles.hint}>
                Page {list.data.page} of {list.data.pages} · {list.data.total} orders
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
