import { Suspense } from "react";

import { LoadingState } from "@/components/admin/Kit";
import { ProductEditor } from "./ProductEditor";

export default function EditProductPage() {
  return (
    <Suspense fallback={<LoadingState />}>
      <ProductEditor />
    </Suspense>
  );
}
