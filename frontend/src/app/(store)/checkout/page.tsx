import type { Metadata } from "next";

import { Suspense } from "react";

import { CheckoutView } from "@/components/checkout/CheckoutView";
import { Loader } from "@/components/ui/Loader";
import { getSiteContent } from "@/lib/content";

export const metadata: Metadata = { title: "Checkout", robots: { index: false, follow: false } };

/** Client-rendered from the checkout API: every amount is calculated by the backend. */
export default function CheckoutPage() {
  return (
    <Suspense fallback={<Loader label="Preparing your checkout…" />}>
      <Checkout />
    </Suspense>
  );
}

async function Checkout() {
  const { shipping } = (await getSiteContent()).commerce;
  return <CheckoutView delivery={{ message: shipping.message, estimate: shipping.estimate }} />;
}
