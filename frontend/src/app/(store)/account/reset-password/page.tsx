import type { Metadata } from "next";
import { Suspense } from "react";

import { ResetPassword } from "@/components/account/PasswordReset";
import { Loader } from "@/components/ui/Loader";

export const metadata: Metadata = {
  title: "Choose a new password",
  robots: { index: false, follow: false },
  referrer: "no-referrer", // the reset token is in the URL: never leak it to other sites
};

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<Loader />}>
      <ResetPassword />
    </Suspense>
  );
}
