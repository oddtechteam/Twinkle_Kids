"use client";

import Link from "next/link";
import { Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { GroupForm, categoryPayload, emptyGroup } from "@/components/admin/CatalogGroupForm";
import { AdminPage, type Column, DataTable, ErrorState, LoadingState, Pill, Toggle, adminStyles as styles } from "@/components/admin/Kit";
import { MediaThumb } from "@/components/admin/Pickers";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { adminApi } from "@/lib/admin/api";
import { useMutation, useResource } from "@/lib/admin/hooks";
import type { AdminCategory } from "@/lib/admin/types";

export default function CategoriesPage() {
  const router = useRouter();
  const list = useResource(adminApi.categories, "categories");
  const { run, pending } = useMutation();
  const [creating, setCreating] = useState(false);

  const byId = new Map((list.data ?? []).map((c) => [c.id, c]));
  // Parents first, children indented under them.
  const ordered = (list.data ?? [])
    .filter((c) => !c.parent_id || !byId.has(c.parent_id))
    .flatMap((parent) => [parent, ...(list.data ?? []).filter((c) => c.parent_id === parent.id)]);

  const columns: Column<AdminCategory>[] = [
    {
      header: "Category",
      render: (c) => (
        <Link href={`/admin/categories/${c.id}`} className={styles.cellTitle} style={c.parent_id ? { paddingLeft: "var(--space-6)" } : undefined}>
          <span className={styles.thumb}>
            <MediaThumb url={c.image?.url} />
          </span>
          {c.name}
        </Link>
      ),
    },
    { header: "Slug", render: (c) => <span className={styles.muted}>/{c.slug}</span> },
    { header: "Order", render: (c) => c.display_order },
    { header: "Products order", render: (c) => (c.custom_product_ordering ? <Pill tone="green">Custom</Pill> : <Pill tone="grey">Store default</Pill>) },
    {
      header: "Visible",
      align: "end",
      render: (c) => (
        <Toggle
          label={c.is_active ? "Visible" : "Hidden"}
          checked={c.is_active}
          onChange={async (value) => {
            const res = await run(() => adminApi.setCategoryActive(c.id, value), { success: value ? "Category shown" : "Category hidden" });
            if (res.ok) list.setData((rows) => rows?.map((r) => (r.id === c.id ? { ...r, is_active: value } : r)));
          }}
        />
      ),
    },
  ];

  return (
    <AdminPage
      title="Categories"
      breadcrumbs={[{ label: "Categories" }]}
      actions={
        <Button iconStart={<Plus aria-hidden="true" />} onClick={() => setCreating(true)}>
          New category
        </Button>
      }
    >
      {list.error && <ErrorState message={list.error} onRetry={list.reload} />}
      {list.loading && !list.data && <LoadingState label="Loading categories…" />}
      {list.data && <DataTable columns={columns} rows={ordered} rowKey={(c) => c.id} empty={<p className={styles.hint}>No categories yet.</p>} />}
      <Dialog open={creating} onClose={() => setCreating(false)} title="New category">
        <GroupForm
          kind="category"
          initial={emptyGroup()}
          parents={(list.data ?? []).filter((c) => !c.parent_id).map((c) => ({ value: c.id, label: c.name }))}
          submitLabel="Create category"
          pending={pending}
          onSubmit={async (state) => {
            const res = await run(() => adminApi.createCategory(categoryPayload(state)), { success: "Category created" });
            if (res.ok) router.push(`/admin/categories/${res.result.id}`);
          }}
        />
      </Dialog>
    </AdminPage>
  );
}
