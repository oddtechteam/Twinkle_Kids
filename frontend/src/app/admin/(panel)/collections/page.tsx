"use client";

import Link from "next/link";
import { Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { GroupForm, collectionPayload, emptyGroup } from "@/components/admin/CatalogGroupForm";
import { AdminPage, type Column, DataTable, ErrorState, StatusPill, adminStyles as styles } from "@/components/admin/Kit";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { adminApi } from "@/lib/admin/api";
import { useMutation, useResource } from "@/lib/admin/hooks";
import type { AdminCollection } from "@/lib/admin/types";

export default function CollectionsPage() {
  const router = useRouter();
  const list = useResource(adminApi.collections, "collections");
  const { run, pending } = useMutation();
  const [creating, setCreating] = useState(false);

  const columns: Column<AdminCollection>[] = [
    {
      header: "Collection",
      render: (c) => (
        <Link href={`/admin/collections/${c.id}`} className={styles.cellTitle}>
          {c.name}
        </Link>
      ),
    },
    { header: "Slug", render: (c) => <span className={styles.muted}>/collections/{c.slug}</span> },
    { header: "Products", render: (c) => c.product_count ?? "—" },
    { header: "Order", render: (c) => c.display_order },
    { header: "Status", render: (c) => <StatusPill status={c.status} /> },
    {
      header: "Actions",
      align: "end",
      render: (c) => (
        <Button
          size="sm"
          variant="ghost"
          onClick={async () => {
            const next = c.status === "published" ? "draft" : "published";
            const res = await run(() => adminApi.setCollectionStatus(c.id, next), {
              success: next === "published" ? "Collection published" : "Collection unpublished",
            });
            if (res.ok) list.setData((rows) => rows?.map((r) => (r.id === c.id ? { ...r, status: next } : r)));
          }}
        >
          {c.status === "published" ? "Unpublish" : "Publish"}
        </Button>
      ),
    },
  ];

  return (
    <AdminPage
      title="Collections"
      description="Curated groups such as “Festive edit” or “Summer cottons”. Each collection keeps its own product order."
      breadcrumbs={[{ label: "Collections" }]}
      actions={
        <Button iconStart={<Plus aria-hidden="true" />} onClick={() => setCreating(true)}>
          New collection
        </Button>
      }
    >
      {list.error && <ErrorState message={list.error} onRetry={list.reload} />}
      {list.data && <DataTable columns={columns} rows={list.data} rowKey={(c) => c.id} empty={<p className={styles.hint}>No collections yet.</p>} />}
      <Dialog open={creating} onClose={() => setCreating(false)} title="New collection">
        <GroupForm
          kind="collection"
          initial={emptyGroup()}
          submitLabel="Create collection"
          pending={pending}
          onSubmit={async (state) => {
            const res = await run(() => adminApi.createCollection(collectionPayload(state)), { success: "Collection created" });
            if (res.ok) router.push(`/admin/collections/${res.result.id}`);
          }}
        />
      </Dialog>
    </AdminPage>
  );
}
