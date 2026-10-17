"use client";

import { useRouter } from "next/navigation";
import { LogIn, Sparkles } from "lucide-react";
import { type FormEvent, useState } from "react";

import { Card, TextInput, adminStyles as styles } from "@/components/admin/Kit";
import { Button } from "@/components/ui/Button";
import { adminApi } from "@/lib/admin/api";
import { ApiError } from "@/lib/api/client";

/** Staff sign-in. Uses the existing session-cookie auth (FastAPI /auth/login). */
export default function AdminLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      const user = await adminApi.login(email, password);
      if (!user.is_staff) {
        await adminApi.logout().catch(() => undefined);
        setError("This account does not have admin access.");
        return;
      }
      const next = new URLSearchParams(window.location.search).get("next");
      router.replace(next && next.startsWith("/admin") ? next : "/admin");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Sign-in failed. Please try again.");
    } finally {
      setPending(false);
    }
  };

  return (
    <main className={styles.center} style={{ minHeight: "100dvh" }}>
      <div className={styles.loginCard}>
        <Card>
          <div style={{ display: "grid", gap: "var(--space-2)" }}>
            <p className={styles.navHeading} style={{ padding: 0, color: "var(--tk-gold-text)" }}>
              <Sparkles size={12} aria-hidden="true" /> Twinkle Kids
            </p>
            <h1 className={styles.pageTitle} style={{ marginTop: 0 }}>
              Admin sign in
            </h1>
          </div>
          <form onSubmit={submit} className={styles.stack} noValidate>
            <TextInput label="Email" type="email" autoComplete="username" value={email} onChange={setEmail} required />
            <TextInput
              label="Password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={setPassword}
              required
            />
            {error && (
              <p className={styles.errorText} role="alert">
                {error}
              </p>
            )}
            <Button type="submit" fullWidth loading={pending} iconStart={<LogIn aria-hidden="true" />}>
              Sign in
            </Button>
          </form>
        </Card>
      </div>
    </main>
  );
}
