"use client";

import { useState } from "react";

import { AdminPage, Card, ErrorState, LoadingState, TextInput, adminStyles as styles } from "@/components/admin/Kit";
import { Button } from "@/components/ui/Button";
import { useResource } from "@/lib/admin/hooks";
import { opsApi } from "@/lib/admin/operations";
import { formatMoney } from "@/lib/format";

function Stat({ label, value, note }: { label: string; value: string | number; note?: string }) {
  return (
    <div className={styles.stat}>
      <span className={styles.statLabel}>{label}</span>
      <span className={styles.statValue}>{value}</span>
      {note && <span className={styles.statNote}>{note}</span>}
    </div>
  );
}

const isoDay = (d: Date) => d.toISOString().slice(0, 10);

export default function AnalyticsPage() {
  const [start, setStart] = useState(() => isoDay(new Date(Date.now() - 29 * 86_400_000)));
  const [end, setEnd] = useState(() => isoDay(new Date()));
  const [range, setRange] = useState({ start, end });
  const report = useResource(() => opsApi.analytics(range), `${range.start}-${range.end}`);
  const a = report.data;
  const maxDay = a ? Math.max(1, ...a.by_day.map((d) => d.website_orders + d.whatsapp_orders)) : 1;
  const pct = (part: number, whole: number) => (whole ? `${Math.round((part / whole) * 100)}%` : "—");

  return (
    <AdminPage
      title="Analytics"
      description="Built only from real orders and requests in the database. Order value is not revenue; revenue counts only payments you've recorded."
    >
      <form
        className={styles.toolbar}
        onSubmit={(e) => {
          e.preventDefault();
          if (start && end && start <= end) setRange({ start, end });
        }}
      >
        <TextInput label="From" type="date" value={start} onChange={setStart} />
        <TextInput label="To" type="date" value={end} onChange={setEnd} />
        <Button type="submit" size="sm" variant="outline" disabled={!start || !end || start > end}>
          Apply
        </Button>
      </form>
      {report.error && <ErrorState message={report.error} onRetry={report.reload} />}
      {report.loading && !a && <LoadingState label="Crunching numbers…" />}
      {a && (
        <div className={styles.stack}>
          <div className={styles.statGrid}>
            <Stat label="Orders placed" value={a.orders_placed} note={`${a.website_orders} website · ${a.whatsapp_orders} via WhatsApp`} />
            <Stat label="Cancelled" value={a.orders_cancelled} />
            <Stat label="Order value placed" value={formatMoney(a.order_value_placed)} note={a.average_order_value ? `Avg ${formatMoney(a.average_order_value)}` : undefined} />
            <Stat label="Payments recorded" value={formatMoney(a.payments_recorded)} note={`Refunds recorded ${formatMoney(a.refunds_recorded)}`} />
          </div>
          <div className={styles.statGrid}>
            <Stat label="WhatsApp requests" value={a.whatsapp_requests} note="Opened WhatsApp — not proof a message was sent" />
            <Stat label="Confirmed contacted" value={a.whatsapp_contacted} note={pct(a.whatsapp_contacted, a.whatsapp_requests)} />
            <Stat label="Converted to orders" value={a.whatsapp_converted} note={pct(a.whatsapp_converted, a.whatsapp_requests)} />
          </div>

          <Card title="Orders per day" hint={`${a.start} to ${a.end}`}>
            <div className={styles.chart} role="img" aria-label={`${a.orders_placed} orders between ${a.start} and ${a.end}`}>
              {a.by_day.map((d) => {
                const total = d.website_orders + d.whatsapp_orders;
                return (
                  <span
                    key={d.day}
                    className={styles.bar}
                    data-empty={total === 0}
                    title={`${d.day}: ${d.website_orders} website, ${d.whatsapp_orders} WhatsApp · ${formatMoney(d.order_value)}`}
                    style={{ height: `${Math.max(4, (total / maxDay) * 100)}%` }}
                  />
                );
              })}
            </div>
          </Card>

          <div className={styles.twoCol}>
            <Card title="Top products" hint="By units in non-cancelled orders">
              {a.top_products.length === 0 ? (
                <p className={styles.hint}>No orders in this period.</p>
              ) : (
                <ul className={styles.list}>
                  {a.top_products.map((p) => (
                    <li key={p.product_id ?? p.product_name} className={styles.listRow}>
                      <span>{p.product_name}</span>
                      <strong>
                        {p.units} · {formatMoney(p.order_value)}
                      </strong>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
            <Card title="Categories">
              {a.categories.length === 0 ? (
                <p className={styles.hint}>No orders in this period.</p>
              ) : (
                <ul className={styles.list}>
                  {a.categories.map((c) => (
                    <li key={c.category} className={styles.listRow}>
                      <span>{c.category}</span>
                      <strong>
                        {c.units} · {formatMoney(c.order_value)}
                      </strong>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>

          <Card title="Coupon usage">
            {a.coupons.length === 0 ? (
              <p className={styles.hint}>No coupons redeemed in this period.</p>
            ) : (
              <ul className={styles.list}>
                {a.coupons.map((c) => (
                  <li key={c.code} className={styles.listRow}>
                    <span className={styles.mono}>{c.code}</span>
                    <strong>
                      {c.redemptions} uses · {formatMoney(c.discount_given)} off
                    </strong>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      )}
    </AdminPage>
  );
}
