import type { Metadata } from "next";

import { BagView } from "@/components/bag/BagView";
import { getSiteContent } from "@/lib/content";

export const metadata: Metadata = { title: "Shopping bag", robots: { index: false, follow: false } };

/** The bag itself is client-rendered from the cart API (prices and totals are backend-calculated). */
export default async function BagPage() {
  const content = await getSiteContent();
  return <BagView whatsappEnabled={content.commerce.whatsappOrdering} />;
}
