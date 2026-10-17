"use client";

import Link from "next/link";
import { Copy, Plus, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  AdminPage,
  type Column,
  DataTable,
  ErrorState,
  StatusPill,
  adminStyles as styles,
} from "@/components/admin/Kit";
import { MediaThumb } from "@/components/admin/Pickers";
import { Button, ButtonLink } from "@/components/ui/Button";
import { adminApi } from "@/lib/admin/api";
import { useMutation, useResource } from "@/lib/admin/hooks";
import type { AdminProductSummary, ProductStatus } from "@/lib/admin/types";
import { formatMoney } from "@/lib/format";

export default function ProductsPage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [term, setTerm] = useState("");
  const [status, setStatus] = useState<ProductStatus | "">("");
  const [page, setPage] = useState(1);
  const list = useResource(() => adminApi.products({ q: term || undefined, status, page }), `${term}|${status}|${page}`);
  const { run } = useMutation();

  useEffect(() => {
    const t = window.setTimeout(() => {
      setTerm(search.trim());
      setPage(1);
    }, 300);
    return () => window.clearTimeout(t);
  }, [search]);

  const columns: Column<AdminProductSummary>[] = [
    {
      header: "Product",
      render: (p) => (
        <Link href={`/admin/products/${p.id}`} className={styles.cellTitle}>
          <span className={styles.thumb}>
            <MediaThumb url={p.primary_image?.url} />
          </span>
          {p.name}
        </Link>
      ),
    },
    { header: "Status", render: (p) => <StatusPill status={p.status} /> },
    {
      header: "Price",
      render: (p) => (
        <span>
          {formatMoney(p.price.selling_price)}
          {p.price.original_price && <span className={styles.muted}> / MRP {formatMoney(p.price.original_price)}</span>}
        </span>
      ),
    },
    { header: "Stock", render: (p) => (p.in_stock ? "In stock" : <span style={{ color: "var(--tk-danger)" }}>Out of stock</span>) },
    {
      header: "Actions",
      align: "end",
      render: (p) => (
        <div className={styles.rowActions}>
          <Button size="sm" variant="ghost" onClick={() => router.push(`/admin/products/${p.id}`)}>
            Edit
          </Button>
          <Button
            size="sm"
            variant="ghost"
            iconStart={<Copy aria-hidden="true" />}
            onClick={async () => {
              const res = await run(() => adminApi.duplicateProduct(p.id), { success: "Draft copy created" });
              if (res.ok) router.push(`/admin/products/${res.result.id}`);
            }}
          >
            Duplicate
          </Button>
        </div>
      ),
    },
  ];

  return (
    <AdminPage
      title="Products"
      breadcrumbs={[{ label: "Products" }]}
      actions={
        <ButtonLink href="/admin/products/new" iconStart={<Plus aria-hidden="true" />}>
          New product
        </ButtonLink>
      }
    >
      <div className={styles.stack}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-3)" }}>
          <div className={styles.prefixed} style={{ flex: "1 1 16rem" }}>
            <Search size={16} className={styles.prefix} aria-hidden="true" />
            <input className={styles.input} placeholder="Search name or SKU" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search products" />
          </div>
          <select className={styles.select} style={{ width: "auto" }} value={status} onChange={(e) => { setStatus(e.target.value as ProductStatus | ""); setPage(1); }} aria-label="Filter by status">
            <option value="">All statuses</option>
            <option value="active">Active</option>
            <option value="draft">Draft</option>
            <option value="archived">Archived</option>
          </select>
        </div>
        {list.error && <ErrorState message={list.error} onRetry={list.reload} />}
        {list.data && (
          <>
            <DataTable
              columns={columns}
              rows={list.data.items}
              rowKey={(p) => p.id}
              empty={<p className={styles.hint}>{list.loading ? "Loading…" : "No products match."}</p>}
            />
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span className={styles.hint}>
                {list.data.total} products · page {list.data.page} of {list.data.pages}
              </span>
              <div className={styles.actions}>
                <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                  Previous
                </Button>
                <Button size="sm" variant="outline" disabled={page >= list.data.pages} onClick={() => setPage((p) => p + 1)}>
                  Next
                </Button>
              </div>
            </div>
          </>
        )}
      </div>
    </AdminPage>
  );
}
