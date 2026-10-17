"use client";

import { ExternalLink } from "lucide-react";
import { useParams } from "next/navigation";

import { GroupForm, collectionPayload } from "@/components/admin/CatalogGroupForm";
import { AdminPage, ErrorState, LoadingState, StatusPill, adminStyles as styles } from "@/components/admin/Kit";
import { ProductOrdering } from "@/components/admin/ProductOrdering";
import { ButtonLink } from "@/components/ui/Button";
import { adminApi } from "@/lib/admin/api";
import { useMutation, useResource } from "@/lib/admin/hooks";

export function CollectionEditor() {
  const { id } = useParams<{ id: string }>();
  const collection = useResource(() => adminApi.collection(id), id);
  const products = useResource(() => adminApi.collectionProducts(id), `${id}-products`);
  const { run, pending } = useMutation();

  if (collection.loading && !collection.data) return <LoadingState />;
  if (collection.error) return <ErrorState message={collection.error} onRetry={collection.reload} />;
  const c = collection.data;
  if (!c) return null;

  return (
    <AdminPage
      title={c.name}
      breadcrumbs={[{ label: "Collections", href: "/admin/collections" }, { label: c.name }]}
      actions={
        <>
          <StatusPill status={c.status} />
          {c.status === "published" && (
            <ButtonLink href={`/collections/${c.slug}`} target="_blank" size="sm" variant="ghost" iconStart={<ExternalLink aria-hidden="true" />}>
              View
            </ButtonLink>
          )}
        </>
      }
    >
      <div className={styles.stack}>
        <GroupForm
          key={`${c.id}-${c.status}`}
          kind="collection"
          initial={{
            name: c.name,
            slug: c.slug,
            description: c.description ?? "",
            image_media_id: c.image_media_id,
            display_order: String(c.display_order),
            seo_title: c.seo_title ?? "",
            seo_description: c.seo_description ?? "",
            parent_id: "",
            is_active: true,
            custom_product_ordering: false,
            status: c.status,
          }}
          submitLabel="Save collection"
          pending={pending}
          onSubmit={async (state) => {
            const res = await run(() => adminApi.updateCollection(c.id, collectionPayload(state)), { success: "Collection saved" });
            if (res.ok) collection.reload();
          }}
        />
        {products.error && <ErrorState message={products.error} onRetry={products.reload} />}
        {products.data && (
          <ProductOrdering
            key={`${c.id}-products`}
            title="Products in this collection"
            hint="Drag to set the order shown on the collection page. It does not change category or homepage ordering."
            initial={products.data}
            onSave={(ids) => adminApi.setCollectionProducts(c.id, ids)}
          />
        )}
      </div>
    </AdminPage>
  );
}
