import type { Metadata } from "next";
import { ShoppingBag } from "lucide-react";

import { ButtonLink } from "@/components/ui/Button";
import { InfoPage } from "@/components/ui/InfoPage";

export const metadata: Metadata = { title: "Shopping bag", robots: { index: false } };

/** Placeholder until the server-side cart API (backend-calculated totals) is integrated. */
export default function BagPage() {
  return (
    <InfoPage
      breadcrumbs={[{ label: "Home", href: "/" }, { label: "Shopping bag" }]}
      icon={<ShoppingBag aria-hidden="true" size={26} />}
      title="Your bag is empty"
      description="Online bag and checkout are opening soon. In the meantime, save your favourite styles to your wishlist."
      action={
        <>
          <ButtonLink href="/shop">Continue shopping</ButtonLink>
          <ButtonLink href="/wishlist" variant="outline">
            View wishlist
          </ButtonLink>
        </>
      }
    />
  );
}
