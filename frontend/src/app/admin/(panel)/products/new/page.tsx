"use client";

import { useRouter } from "next/navigation";

import { AdminPage } from "@/components/admin/Kit";
import { ProductForm, emptyProduct } from "@/components/admin/ProductForm";
import { adminApi } from "@/lib/admin/api";
import { useMutation } from "@/lib/admin/hooks";

export default function NewProductPage() {
  const router = useRouter();
  const { run, pending } = useMutation();
  return (
    <AdminPage title="New product" breadcrumbs={[{ label: "Products", href: "/admin/products" }, { label: "New" }]}>
      <ProductForm
        initial={emptyProduct()}
        submitLabel="Create product"
        pending={pending}
        onSubmit={async (payload) => {
          const res = await run(() => adminApi.createProduct(payload), { success: "Product created" });
          if (res.ok) router.replace(`/admin/products/${res.result.id}`);
        }}
      />
    </AdminPage>
  );
}
