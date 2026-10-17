"use client";

import { ExternalLink } from "lucide-react";
import { useParams } from "next/navigation";

import { GroupForm, categoryPayload } from "@/components/admin/CatalogGroupForm";
import { AdminPage, ErrorState, LoadingState, Pill, adminStyles as styles } from "@/components/admin/Kit";
import { ProductOrdering } from "@/components/admin/ProductOrdering";
import { ButtonLink } from "@/components/ui/Button";
import { adminApi } from "@/lib/admin/api";
import { useMutation, useResource } from "@/lib/admin/hooks";

export function CategoryEditor() {
  const { id } = useParams<{ id: string }>();
  const category = useResource(() => adminApi.category(id), id);
  const parents = useResource(adminApi.categories, "categories");
  const { run, pending } = useMutation();

  if (category.loading && !category.data) return <LoadingState />;
  if (category.error) return <ErrorState message={category.error} onRetry={category.reload} />;
  const c = category.data;
  if (!c) return null;

  return (
    <AdminPage
      title={c.name}
      breadcrumbs={[{ label: "Categories", href: "/admin/categories" }, { label: c.name }]}
      actions={
        <>
          <Pill tone={c.is_active ? "green" : "grey"}>{c.is_active ? "Visible" : "Hidden"}</Pill>
          {c.is_active && (
            <ButtonLink href={`/category/${c.slug}`} target="_blank" size="sm" variant="ghost" iconStart={<ExternalLink aria-hidden="true" />}>
              View
            </ButtonLink>
          )}
        </>
      }
    >
      <div className={styles.stack}>
        <GroupForm
          key={c.id}
          kind="category"
          initial={{
            name: c.name,
            slug: c.slug,
            description: c.description ?? "",
            image_media_id: c.image_media_id,
            display_order: String(c.display_order),
            seo_title: c.seo_title ?? "",
            seo_description: c.seo_description ?? "",
            parent_id: c.parent_id ?? "",
            is_active: c.is_active,
            custom_product_ordering: c.custom_product_ordering,
            status: "draft",
          }}
          parents={(parents.data ?? []).filter((p) => p.id !== c.id && !p.parent_id).map((p) => ({ value: p.id, label: p.name }))}
          submitLabel="Save category"
          pending={pending}
          onSubmit={async (state) => {
            const res = await run(() => adminApi.updateCategory(c.id, categoryPayload(state)), { success: "Category saved" });
            if (res.ok) category.reload();
          }}
        />
        <ProductOrdering
          key={`${c.id}-products`}
          title="Products in this category"
          hint={
            c.custom_product_ordering
              ? "This order is used on the category page when sorted by “Featured”. It does not affect collections or the homepage."
              : "Turn on “Use custom product order” above for this order to be used on the category page."
          }
          initial={c.products}
          onSave={(ids) => adminApi.setCategoryProducts(c.id, ids)}
        />
      </div>
    </AdminPage>
  );
}
