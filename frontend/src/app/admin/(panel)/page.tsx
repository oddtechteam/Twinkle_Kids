"use client";

import Link from "next/link";

import { AdminPage, Card, ErrorState, LoadingState, adminStyles as styles } from "@/components/admin/Kit";
import { adminApi } from "@/lib/admin/api";
import { useResource } from "@/lib/admin/hooks";
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

const ACTIONS: Record<string, string> = {
  "product.created": "created a product",
  "product.updated": "updated a product",
  "product.duplicated": "duplicated a product",
  "product.status_changed": "changed a product status",
  "homepage.published": "published the homepage",
  "settings.updated": "updated store settings",
};

export default function DashboardPage() {
  const dashboard = useResource(adminApi.dashboard, "dashboard");

  if (dashboard.loading && !dashboard.data) return <LoadingState />;
  if (dashboard.error) return <ErrorState message={dashboard.error} onRetry={dashboard.reload} />;
  const d = dashboard.data;
  if (!d) return null;

  const maxDay = Math.max(1, ...d.orders_by_day.map((x) => x.orders));
  const ordersLast30 = d.orders_by_day.reduce((sum, x) => sum + x.orders, 0);

  return (
    <AdminPage title="Dashboard" description="Live figures from the store database.">
      <div className={styles.stack}>
        <div className={styles.statGrid}>
          <Stat label="Products" value={d.products_total} note={`${d.products_active} active · ${d.products_draft} draft · ${d.products_archived} archived`} />
          <Stat label="Low-stock variants" value={d.low_stock_count} note={`${d.out_of_stock_count} out of stock`} />
          <Stat label="New orders" value={d.orders_new} note="Awaiting confirmation" />
          <Stat
            label="WhatsApp requests"
            value={d.whatsapp_initiated}
            note={`Opened WhatsApp (not proof of a message) · ${d.whatsapp_contacted} confirmed contacted`}
          />
        </div>

        <div className={styles.statGrid}>
          <Stat label="Order value placed" value={formatMoney(d.order_value_placed)} note="All non-cancelled orders — not revenue" />
          <Stat label="Confirmed order value" value={formatMoney(d.order_value_confirmed)} note="Confirmed through delivered" />
          <Stat label="Recorded paid revenue" value={formatMoney(d.revenue_paid)} note="Only orders with payment recorded as paid" />
        </div>

        <div className={styles.twoCol}>
          <Card title="Orders, last 30 days" hint={`${ordersLast30} orders · ${d.orders_total} all time`}>
            <div className={styles.chart} role="img" aria-label={`${ordersLast30} orders in the last 30 days`}>
              {d.orders_by_day.map((day) => (
                <span
                  key={day.day}
                  className={styles.bar}
                  data-empty={day.orders === 0}
                  title={`${day.day}: ${day.orders}`}
                  style={{ height: `${Math.max(4, (day.orders / maxDay) * 100)}%` }}
                />
              ))}
            </div>
          </Card>

          <Card title="Top products" hint="Units sold, last 30 days">
            {d.top_products.length === 0 ? (
              <p className={styles.hint}>
                Not enough order data yet (shown after {d.top_products_min_orders} orders in 30 days).
              </p>
            ) : (
              <ul className={styles.list}>
                {d.top_products.map((p) => (
                  <li key={p.product_name} className={styles.listRow}>
                    <span>{p.product_name}</span>
                    <strong>{p.units}</strong>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>

        <div className={styles.twoCol}>
          <Card title="Inventory warnings" hint="Active variants at or below their low-stock threshold">
            {d.low_stock.length === 0 ? (
              <p className={styles.hint}>No inventory warnings.</p>
            ) : (
              <ul className={styles.list}>
                {d.low_stock.map((item) => (
                  <li key={item.sku} className={styles.listRow}>
                    <Link href={`/admin/products/${item.product_id}`}>
                      {item.product_name}
                      {item.variant_label && <span className={styles.muted}> · {item.variant_label}</span>}
                    </Link>
                    <strong style={{ color: item.stock_quantity === 0 ? "var(--tk-danger)" : undefined }}>
                      {item.stock_quantity} left
                    </strong>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card title="Recent activity">
            {d.recent_activity.length === 0 ? (
              <p className={styles.hint}>No activity recorded yet.</p>
            ) : (
              <ul className={styles.list}>
                {d.recent_activity.map((a, i) => (
                  <li key={i} className={styles.listRow} style={{ flexDirection: "column", gap: 2 }}>
                    <span>
                      <strong>{a.actor_email ?? "System"}</strong> {ACTIONS[a.action] ?? a.action}
                    </span>
                    <span className={styles.hint}>{new Date(a.created_at).toLocaleString("en-IN")}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </AdminPage>
  );
}
