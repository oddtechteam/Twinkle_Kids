"use client";

import { useParams, useRouter } from "next/navigation";
import { Archive, Copy, ExternalLink, RotateCcw } from "lucide-react";
import { useState } from "react";

import { AdminPage, ConfirmDialog, ErrorState, LoadingState, StatusPill } from "@/components/admin/Kit";
import { ProductForm, fromDetail } from "@/components/admin/ProductForm";
import { Button, ButtonLink } from "@/components/ui/Button";
import { adminApi } from "@/lib/admin/api";
import { useMutation, useResource } from "@/lib/admin/hooks";

export function ProductEditor() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const product = useResource(() => adminApi.product(id), id);
  const { run, pending } = useMutation();
  const [confirmArchive, setConfirmArchive] = useState(false);
  const [version, setVersion] = useState(0);

  if (product.loading && !product.data) return <LoadingState />;
  if (product.error) return <ErrorState message={product.error} onRetry={product.reload} />;
  const p = product.data;
  if (!p) return null;

  const archived = p.status === "archived";

  return (
    <AdminPage
      title={p.name}
      breadcrumbs={[{ label: "Products", href: "/admin/products" }, { label: p.name }]}
      actions={
        <>
          <StatusPill status={p.status} />
          {p.status === "active" && (
            <ButtonLink href={`/products/${p.slug}`} target="_blank" variant="ghost" size="sm" iconStart={<ExternalLink aria-hidden="true" />}>
              View
            </ButtonLink>
          )}
          <Button
            size="sm"
            variant="outline"
            iconStart={<Copy aria-hidden="true" />}
            onClick={async () => {
              const res = await run(() => adminApi.duplicateProduct(p.id), { success: "Draft copy created" });
              if (res.ok) router.push(`/admin/products/${res.result.id}`);
            }}
          >
            Duplicate
          </Button>
          {archived ? (
            <Button
              size="sm"
              variant="outline"
              iconStart={<RotateCcw aria-hidden="true" />}
              onClick={async () => {
                const res = await run(() => adminApi.setProductStatus(p.id, "draft"), { success: "Restored as draft" });
                if (res.ok) {
                  product.setData(res.result);
                  setVersion((v) => v + 1);
                }
              }}
            >
              Restore
            </Button>
          ) : (
            <Button size="sm" variant="outline" iconStart={<Archive aria-hidden="true" />} onClick={() => setConfirmArchive(true)}>
              Archive
            </Button>
          )}
        </>
      }
    >
      <ProductForm
        key={`${p.id}-${version}`}
        initial={fromDetail(p)}
        saved={p}
        submitLabel="Save changes"
        pending={pending}
        onSubmit={async (payload) => {
          const res = await run(() => adminApi.updateProduct(p.id, payload), { success: "Product saved" });
          if (res.ok) {
            product.setData(res.result);
            setVersion((v) => v + 1);
          }
        }}
      />
      <ConfirmDialog
        open={confirmArchive}
        title="Archive this product?"
        message="Archived products disappear from the storefront but keep their order history. You can restore them later."
        confirmLabel="Archive product"
        destructive
        pending={pending}
        onClose={() => setConfirmArchive(false)}
        onConfirm={async () => {
          const res = await run(() => adminApi.setProductStatus(p.id, "archived"), { success: "Product archived" });
          setConfirmArchive(false);
          if (res.ok) {
            product.setData(res.result);
            setVersion((v) => v + 1);
          }
        }}
      />
    </AdminPage>
  );
}
