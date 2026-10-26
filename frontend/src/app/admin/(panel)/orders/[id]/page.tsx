import { Suspense } from "react";

import { LoadingState } from "@/components/admin/Kit";
import { OrderDetail } from "./OrderDetail";

export default function AdminOrderPage() {
  return (
    <Suspense fallback={<LoadingState label="Loading order…" />}>
      <OrderDetail />
    </Suspense>
  );
}
