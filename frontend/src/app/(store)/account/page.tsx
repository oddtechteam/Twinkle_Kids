import type { Metadata } from "next";
import { Suspense } from "react";

import { AccountView } from "@/components/account/AccountView";
import { Loader } from "@/components/ui/Loader";

export const metadata: Metadata = { title: "My account", robots: { index: false, follow: false } };

/** Sign in, create an account, or see the signed-in profile (existing /api/v1/auth endpoints). */
export default function AccountPage() {
  return (
    <Suspense fallback={<Loader label="Opening your account…" />}>
      <AccountView />
    </Suspense>
  );
}
