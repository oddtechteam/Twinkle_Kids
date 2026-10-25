"use client";

import Link from "next/link";
import { Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { AdminPage, type Column, DataTable, ErrorState, LoadingState, StatusPill, TextInput, adminStyles as styles } from "@/components/admin/Kit";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { adminApi } from "@/lib/admin/api";
import { useMutation, useResource } from "@/lib/admin/hooks";
import type { WebsitePage } from "@/lib/admin/types";
import { formatDateTime } from "@/lib/format";

export default function PagesListPage() {
  const router = useRouter();
  const list = useResource(adminApi.pages, "pages");
  const { run, pending } = useMutation();
  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");

  const create = async (event: FormEvent) => {
    event.preventDefault();
    const res = await run(
      () => adminApi.createPage({ title: title.trim(), slug: slug.trim() || null, status: "draft", content: { blocks: [] } }),
      { success: "Draft page created" },
    );
    if (res.ok) router.push(`/admin/pages/${res.result.id}`);
  };

  const columns: Column<WebsitePage>[] = [
    {
      header: "Page",
      render: (p) => (
        <Link href={`/admin/pages/${p.id}`} className={styles.cellTitle}>
          {p.title}
        </Link>
      ),
    },
    { header: "URL", render: (p) => <span className={styles.muted}>/pages/{p.slug}</span> },
    { header: "Status", render: (p) => <StatusPill status={p.status} /> },
    { header: "Updated", render: (p) => (p.updated_at ? formatDateTime(p.updated_at) : "—") },
  ];

  return (
    <AdminPage
      title="Pages & FAQs"
      description="Policies, FAQs, size guide and other content pages. Text only — no HTML."
      breadcrumbs={[{ label: "Pages" }]}
      actions={
        <Button iconStart={<Plus aria-hidden="true" />} onClick={() => setCreating(true)}>
          New page
        </Button>
      }
    >
      {list.error && <ErrorState message={list.error} onRetry={list.reload} />}
      {list.loading && !list.data && <LoadingState label="Loading pages…" />}
      {list.data && <DataTable columns={columns} rows={list.data} rowKey={(p) => p.id} empty={<p className={styles.hint}>No pages yet.</p>} />}
      <Dialog open={creating} onClose={() => setCreating(false)} title="New page">
        <form onSubmit={create} className={styles.stack} noValidate>
          <TextInput label="Title" value={title} onChange={setTitle} maxLength={160} required />
          <TextInput label="Slug" hint="Leave empty to generate from the title, e.g. shipping-policy" value={slug} onChange={setSlug} maxLength={160} />
          <Button type="submit" loading={pending} disabled={!title.trim()}>
            Create draft
          </Button>
        </form>
      </Dialog>
    </AdminPage>
  );
}
