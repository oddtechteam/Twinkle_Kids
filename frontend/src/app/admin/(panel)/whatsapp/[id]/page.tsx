import { Suspense } from "react";

import { LoadingState } from "@/components/admin/Kit";
import { WhatsAppRequestDetail } from "./WhatsAppRequestDetail";

export default function AdminWhatsAppRequestPage() {
  return (
    <Suspense fallback={<LoadingState label="Loading request…" />}>
      <WhatsAppRequestDetail />
    </Suspense>
  );
}
