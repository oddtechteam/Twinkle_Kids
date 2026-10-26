import type { Metadata } from "next";

import { ForgotPassword } from "@/components/account/PasswordReset";

export const metadata: Metadata = { title: "Forgot password", robots: { index: false, follow: false } };

export default function ForgotPasswordPage() {
  return <ForgotPassword />;
}
