import { Suspense } from "react";

import { LoadingState } from "@/components/admin/Kit";
import { CategoryEditor } from "./CategoryEditor";

export default function EditCategoryPage() {
  return (
    <Suspense fallback={<LoadingState />}>
      <CategoryEditor />
    </Suspense>
  );
}
