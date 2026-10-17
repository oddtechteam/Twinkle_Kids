import { Suspense } from "react";

import { LoadingState } from "@/components/admin/Kit";
import { PageEditor } from "./PageEditor";

export default function EditWebsitePage() {
  return (
    <Suspense fallback={<LoadingState />}>
      <PageEditor />
    </Suspense>
  );
}
