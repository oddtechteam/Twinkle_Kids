"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { KeyRound, MailCheck } from "lucide-react";
import { type FormEvent, useState } from "react";

import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Button, ButtonLink } from "@/components/ui/Button";
import { TextField } from "@/components/ui/Form";
import { confirmPasswordReset, requestPasswordReset } from "@/lib/account/api";
import { ApiError } from "@/lib/api/client";
import styles from "./AccountView.module.css";

const CRUMBS = [
  { label: "Home", href: "/" },
  { label: "My account", href: "/account" },
  { label: "Password" },
];

function message(error: unknown): string {
  if (error instanceof ApiError) return error.status >= 500 ? "Something went wrong. Please try again." : error.message;
  return "We couldn't reach the store. Check your connection and try again.";
}

/** Step 1: ask for a reset link. The answer is the same whether or not the email exists. */
export function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await requestPasswordReset(email.trim());
      setSent(true);
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={`container-narrow ${styles.page}`}>
      <Breadcrumbs items={CRUMBS} />
      <section className={styles.card} aria-labelledby="forgot-title">
        <span className={styles.icon}>{sent ? <MailCheck aria-hidden="true" size={26} /> : <KeyRound aria-hidden="true" size={26} />}</span>
        <h1 id="forgot-title" className={styles.title}>
          {sent ? "Check your email" : "Forgot your password?"}
        </h1>
        {sent ? (
          <>
            <p className={styles.lede}>
              If an account exists for <strong>{email}</strong>, we&apos;ve sent a link to choose a new password. It expires soon and works once.
            </p>
            <ButtonLink href="/account" variant="outline">
              Back to sign in
            </ButtonLink>
          </>
        ) : (
          <form className={styles.form} onSubmit={submit}>
            <p className={styles.lede}>Enter your account email and we&apos;ll send you a reset link.</p>
            <TextField label="Email" type="email" autoComplete="email" required maxLength={254} value={email} onChange={(e) => setEmail(e.target.value)} />
            {error && (
              <p className={styles.error} role="alert">
                {error}
              </p>
            )}
            <Button type="submit" size="lg" fullWidth loading={busy}>
              Send reset link
            </Button>
            <Link href="/account" className={styles.inlineLink}>
              Remembered it? Sign in
            </Link>
          </form>
        )}
      </section>
    </div>
  );
}

/** Step 2: the link from the email lands here with a single-use token. */
export function ResetPassword() {
  const token = useSearchParams().get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (password.length < 10) return setError("Your new password needs at least 10 characters.");
    if (password !== confirm) return setError("The two passwords don't match.");
    setBusy(true);
    try {
      await confirmPasswordReset(token, password);
      setDone(true);
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={`container-narrow ${styles.page}`}>
      <Breadcrumbs items={CRUMBS} />
      <section className={styles.card} aria-labelledby="reset-title">
        <span className={styles.icon}>
          <KeyRound aria-hidden="true" size={26} />
        </span>
        <h1 id="reset-title" className={styles.title}>
          {done ? "Password updated" : "Choose a new password"}
        </h1>
        {done ? (
          <>
            <p className={styles.lede}>You&apos;ve been signed out everywhere for safety. Sign in with your new password.</p>
            <ButtonLink href="/account">Sign in</ButtonLink>
          </>
        ) : !token ? (
          <>
            <p className={styles.lede}>This link is missing its reset code. Please request a new link.</p>
            <ButtonLink href="/account/forgot-password">Request a new link</ButtonLink>
          </>
        ) : (
          <form className={styles.form} onSubmit={submit}>
            <TextField label="New password (10+ characters)" type="password" autoComplete="new-password" required minLength={10} maxLength={128} value={password} onChange={(e) => setPassword(e.target.value)} />
            <TextField label="Confirm new password" type="password" autoComplete="new-password" required maxLength={128} value={confirm} onChange={(e) => setConfirm(e.target.value)} />
            {error && (
              <p className={styles.error} role="alert">
                {error}{" "}
                {/expired|invalid/i.test(error) && (
                  <Link href="/account/forgot-password" className={styles.inlineLink}>
                    Request a new link
                  </Link>
                )}
              </p>
            )}
            <Button type="submit" size="lg" fullWidth loading={busy}>
              Save new password
            </Button>
          </form>
        )}
      </section>
    </div>
  );
}
