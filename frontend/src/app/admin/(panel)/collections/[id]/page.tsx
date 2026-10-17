import { Suspense } from "react";

import { LoadingState } from "@/components/admin/Kit";
import { CollectionEditor } from "./CollectionEditor";

export default function EditCollectionPage() {
  return (
    <Suspense fallback={<LoadingState />}>
      <CollectionEditor />
    </Suspense>
  );
}
