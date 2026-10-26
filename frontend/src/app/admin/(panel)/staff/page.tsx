"use client";

import { type FormEvent, useState } from "react";

import {
  AdminPage,
  Card,
  CheckList,
  type Column,
  ConfirmDialog,
  DataTable,
  ErrorState,
  LoadingState,
  Pill,
  TextInput,
  adminStyles as styles,
} from "@/components/admin/Kit";
import { Button } from "@/components/ui/Button";
import { useMutation, useResource } from "@/lib/admin/hooks";
import { ROLE_LABELS, type StaffMember, type StaffRole, opsApi } from "@/lib/admin/operations";
import { formatDateTime } from "@/lib/format";

const ROLE_OPTIONS = (Object.keys(ROLE_LABELS) as StaffRole[]).map((value) => ({ value, label: ROLE_LABELS[value] }));

export default function StaffPage() {
  const list = useResource(() => opsApi.staff(), "staff");
  const { run, pending } = useMutation();
  const [email, setEmail] = useState("");
  const [roles, setRoles] = useState<string[]>([]);
  const [confirm, setConfirm] = useState(false);

  const columns: Column<StaffMember>[] = [
    { header: "Name", render: (m) => <span className={styles.cellTitle}>{m.full_name}</span> },
    { header: "Email", render: (m) => m.email },
    {
      header: "Roles",
      render: (m) => (
        <div className={styles.rowActions}>
          {m.roles
            .filter((r): r is StaffRole => r in ROLE_LABELS)
            .map((r) => (
              <Pill key={r} tone={r === "owner" ? "red" : "green"}>
                {ROLE_LABELS[r]}
              </Pill>
            ))}
        </div>
      ),
    },
    { header: "Last sign-in", render: (m) => (m.last_login_at ? formatDateTime(m.last_login_at) : "—") },
    {
      header: "",
      render: (m) => (
        <Button
          size="sm"
          variant="ghost"
          onClick={() => {
            setEmail(m.email);
            setRoles(m.roles.filter((r) => r in ROLE_LABELS));
          }}
        >
          Change roles
        </Button>
      ),
    },
  ];

  async function save() {
    const res = await run(() => opsApi.setRoles(email.trim(), roles as StaffRole[]), { success: "Roles updated" });
    setConfirm(false);
    if (res.ok) {
      setEmail("");
      setRoles([]);
      void list.reload();
    }
  }

  return (
    <AdminPage
      title="Staff & roles"
      description="Grant staff roles to people who already have an account (they sign up on the storefront first). Admin accounts are never created here. Changes are audited and sign the person out."
    >
      <div className={styles.twoCol}>
        <div className={styles.stack}>
          {list.error && <ErrorState message={list.error} onRetry={list.reload} />}
          {list.loading && !list.data && <LoadingState label="Loading staff…" />}
          {list.data && <DataTable columns={columns} rows={list.data} rowKey={(m) => m.id} empty={<p className={styles.hint}>No staff yet.</p>} />}
        </div>
        <Card title="Assign roles" hint="Super administrators can do everything; catalogue managers handle products and content; order managers handle orders, WhatsApp requests and inventory.">
          <form
            className={styles.stack}
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              if (email.trim()) setConfirm(true);
            }}
          >
            <TextInput label="Account email" type="email" value={email} onChange={setEmail} required maxLength={254} />
            <CheckList label="Roles" options={ROLE_OPTIONS} selected={roles} onChange={setRoles} />
            <p className={styles.hint}>Leave every role unticked to remove staff access.</p>
            <Button type="submit" disabled={!email.trim() || pending}>
              Save roles
            </Button>
          </form>
        </Card>
      </div>
      <ConfirmDialog
        open={confirm}
        title="Change this person's access?"
        message={`${email} will have: ${roles.length ? roles.map((r) => ROLE_LABELS[r as StaffRole]).join(", ") : "no staff access"}. They'll be signed out so the change applies immediately.`}
        confirmLabel="Save roles"
        destructive={roles.length === 0}
        pending={pending}
        onConfirm={() => void save()}
        onClose={() => setConfirm(false)}
      />
    </AdminPage>
  );
}
