"use client";

import { useState } from "react";

import { AdminPage, type Column, DataTable, ErrorState, LoadingState, Pill, adminStyles as styles } from "@/components/admin/Kit";
import { Button } from "@/components/ui/Button";
import { useResource } from "@/lib/admin/hooks";
import { type AuditEntry, type NotificationEntry, opsApi } from "@/lib/admin/operations";
import { formatDateTime } from "@/lib/format";

/** Audit trail of sensitive admin changes, and the log of customer notification attempts. */
export default function ActivityPage() {
  const [tab, setTab] = useState<"audit" | "notifications">("audit");
  return (
    <AdminPage
      title="Activity & notifications"
      description="Who changed what (prices, stock, orders, roles…) and every customer message we tried to send. A message counts as sent only when the email provider accepted it."
    >
      <div className={styles.tabs} role="group" aria-label="Log">
        <button type="button" className={styles.tab} aria-pressed={tab === "audit"} onClick={() => setTab("audit")}>
          Audit log
        </button>
        <button type="button" className={styles.tab} aria-pressed={tab === "notifications"} onClick={() => setTab("notifications")}>
          Notifications
        </button>
      </div>
      {tab === "audit" ? <AuditLog /> : <NotificationLog />}
    </AdminPage>
  );
}

function AuditLog() {
  const [page, setPage] = useState(1);
  const [action, setAction] = useState("");
  const [term, setTerm] = useState("");
  const list = useResource(() => opsApi.audit({ page, action: term }), `${page}-${term}`);
  const columns: Column<AuditEntry>[] = [
    { header: "When", render: (e) => formatDateTime(e.created_at) },
    { header: "Action", render: (e) => <span className={styles.mono}>{e.action}</span> },
    { header: "By", render: (e) => e.actor_email ?? "System / customer" },
    { header: "Item", render: (e) => `${e.entity_type}${e.entity_id ? ` ${e.entity_id.slice(0, 8)}` : ""}` },
    {
      header: "Details",
      render: (e) => (e.changes ? <code className={styles.mono}>{JSON.stringify(e.changes).slice(0, 160)}</code> : "—"),
    },
  ];
  return (
    <>
      <form
        className={styles.toolbar}
        role="search"
        onSubmit={(e) => {
          e.preventDefault();
          setTerm(action.trim());
          setPage(1);
        }}
      >
        <input className={styles.input} placeholder="Action starts with… e.g. product, order, user.roles" value={action} onChange={(e) => setAction(e.target.value)} aria-label="Filter by action" maxLength={60} />
        <Button type="submit" size="sm" variant="outline">
          Filter
        </Button>
      </form>
      {list.error && <ErrorState message={list.error} onRetry={list.reload} />}
      {list.loading && !list.data && <LoadingState label="Loading activity…" />}
      {list.data && <DataTable columns={columns} rows={list.data.items} rowKey={(e) => e.id} empty={<p className={styles.hint}>No activity recorded.</p>} />}
      {list.data && list.data.pages > 1 && <Pager page={page} pages={list.data.pages} onPage={setPage} />}
    </>
  );
}

function NotificationLog() {
  const [page, setPage] = useState(1);
  const list = useResource(() => opsApi.notifications({ page }), String(page));
  const tone = { sent: "green", failed: "red", skipped: "grey" } as const;
  const columns: Column<NotificationEntry>[] = [
    { header: "When", render: (n) => (n.created_at ? formatDateTime(n.created_at) : "—") },
    { header: "Message", render: (n) => n.subject ?? n.template },
    { header: "To", render: (n) => <span className={styles.mono}>{n.recipient}</span> },
    { header: "Channel", render: (n) => n.channel },
    {
      header: "Result",
      render: (n) => (
        <span>
          <Pill tone={tone[n.status]}>{n.status === "skipped" ? "Not sent" : n.status === "sent" ? "Accepted by provider" : "Failed"}</Pill>
          {n.error && <span className={styles.muted}> {n.error}</span>}
          {n.status === "skipped" && n.provider === "development-log" && <span className={styles.muted}> (development log only)</span>}
        </span>
      ),
    },
  ];
  return (
    <>
      {list.error && <ErrorState message={list.error} onRetry={list.reload} />}
      {list.loading && !list.data && <LoadingState label="Loading notifications…" />}
      {list.data && <DataTable columns={columns} rows={list.data.items} rowKey={(n) => n.id} empty={<p className={styles.hint}>No notifications yet.</p>} />}
      {list.data && list.data.pages > 1 && <Pager page={page} pages={list.data.pages} onPage={setPage} />}
    </>
  );
}

function Pager({ page, pages, onPage }: { page: number; pages: number; onPage: (p: number) => void }) {
  return (
    <div className={styles.pager}>
      <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => onPage(page - 1)}>
        Previous
      </Button>
      <span className={styles.hint}>
        Page {page} of {pages}
      </span>
      <Button size="sm" variant="outline" disabled={page >= pages} onClick={() => onPage(page + 1)}>
        Next
      </Button>
    </div>
  );
}
