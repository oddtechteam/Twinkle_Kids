import type { Metadata } from "next";
import { Suspense } from "react";

import { OrderConfirmation } from "@/components/checkout/OrderConfirmation";
import { Loader } from "@/components/ui/Loader";
import { getSiteContent } from "@/lib/content";

export const metadata: Metadata = { title: "Order received", robots: { index: false, follow: false } };

export default function OrderConfirmationPage({ params }: PageProps<"/order-confirmation/[reference]">) {
  return (
    <Suspense fallback={<Loader label="Loading your order…" />}>
      <ConfirmationBody params={params} />
    </Suspense>
  );
}

async function ConfirmationBody({ params }: Pick<PageProps<"/order-confirmation/[reference]">, "params">) {
  const [{ reference }, content] = await Promise.all([params, getSiteContent()]);
  return <OrderConfirmation reference={decodeURIComponent(reference)} contact={content.contact} storeName={content.brand.name} />;
}
