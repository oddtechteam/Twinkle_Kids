import type { Metadata } from "next";
import { UserRound } from "lucide-react";

import { ButtonLink } from "@/components/ui/Button";
import { InfoPage } from "@/components/ui/InfoPage";

export const metadata: Metadata = { title: "Account", robots: { index: false } };

/** Placeholder until customer sign-in UI is built on the existing /api/v1/auth endpoints. */
export default function AccountPage() {
  return (
    <InfoPage
      breadcrumbs={[{ label: "Home", href: "/" }, { label: "Account" }]}
      icon={<UserRound aria-hidden="true" size={26} />}
      title="Customer accounts are coming soon"
      description="Soon you'll be able to sign in, manage addresses and see your past orders here."
      action={<ButtonLink href="/shop">Continue shopping</ButtonLink>}
    />
  );
}
