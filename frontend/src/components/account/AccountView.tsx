"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Heart, LogOut, Mail, Phone, RotateCcw, ShieldCheck, UserRound } from "lucide-react";
import { type FormEvent, useEffect, useId, useState } from "react";

import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Button, ButtonLink } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/Feedback";
import { TextField } from "@/components/ui/Form";
import { Loader } from "@/components/ui/Loader";
import { useToast } from "@/components/ui/Toast";
import { fetchMe, register, safeNextPath, signIn, signOut } from "@/lib/account/api";
import { ApiError } from "@/lib/api/client";
import type { CustomerProfile } from "@/lib/api/types";
import { useBag } from "@/lib/bag/BagProvider";
import type { OrderPolicy } from "@/lib/content/types";
import { AddressesPanel, OrdersPanel, ProfilePanel } from "./AccountPanels";
import styles from "./AccountView.module.css";

type State = { status: "loading" } | { status: "error" } | { status: "guest" } | { status: "signed-in"; user: CustomerProfile };

const CRUMBS = [{ label: "Home", href: "/" }, { label: "My account" }];

function messageFor(error: unknown): string {
  if (error instanceof ApiError) return error.status >= 500 ? "Something went wrong. Please try again." : error.message;
  return "We couldn't reach the store. Check your connection and try again.";
}

/** Sign in / create an account, or the signed-in customer's overview. */
export function AccountView({ orderPolicy = null }: { orderPolicy?: OrderPolicy | null }) {
  const [state, setState] = useState<State>({ status: "loading" });
  const bag = useBag();
  const router = useRouter();
  const next = safeNextPath(useSearchParams().get("next"));

  async function load() {
    setState({ status: "loading" });
    try {
      const user = await fetchMe();
      setState(user ? { status: "signed-in", user } : { status: "guest" });
    } catch {
      setState({ status: "error" });
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads the session once on mount
    void load();
  }, []);

  async function onSignedIn(user: CustomerProfile) {
    await bag.refresh(); // the API merges any guest bag into the account bag
    if (next) {
      router.push(next);
      return;
    }
    setState({ status: "signed-in", user });
  }

  return (
    <div className={`container-narrow ${styles.page}`}>
      <Breadcrumbs items={CRUMBS} />
      {state.status === "loading" && <Loader label="Opening your account…" />}
      {state.status === "error" && (
        <EmptyState
          tone="error"
          title="We couldn't load your account"
          description="Please check your connection and try again."
          action={
            <Button onClick={() => void load()} iconStart={<RotateCcw aria-hidden="true" />}>
              Try again
            </Button>
          }
        />
      )}
      {state.status === "guest" && <AuthForms onSignedIn={(user) => void onSignedIn(user)} />}
      {state.status === "signed-in" && (
        <Overview
          user={state.user}
          orderPolicy={orderPolicy}
          onSignedOut={async () => {
            await bag.refresh();
            setState({ status: "guest" });
          }}
        />
      )}
    </div>
  );
}

function AuthForms({ onSignedIn }: { onSignedIn: (user: CustomerProfile) => void }) {
  const [mode, setMode] = useState<"sign-in" | "register">("sign-in");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const errorId = useId();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const value = (name: string) => String(form.get(name) ?? "").trim();
    setError(null);
    setBusy(true);
    try {
      const user =
        mode === "sign-in"
          ? await signIn(value("email"), String(form.get("password") ?? ""))
          : await register({
              fullName: value("full_name"),
              email: value("email"),
              phone: value("phone"),
              password: String(form.get("password") ?? ""),
            });
      onSignedIn(user);
    } catch (caught) {
      setError(messageFor(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className={styles.card} aria-labelledby="account-title">
      <span className={styles.icon}>
        <UserRound aria-hidden="true" size={26} />
      </span>
      <h1 id="account-title" className={styles.title}>
        {mode === "sign-in" ? "Welcome back" : "Create your account"}
      </h1>
      <p className={styles.lede}>
        {mode === "sign-in"
          ? "Sign in to keep your bag with you on every device."
          : "Save your bag and check out faster next time."}
      </p>

      <div className={styles.tabs} role="group" aria-label="Choose an option">
        {(["sign-in", "register"] as const).map((tab) => (
          <button
            key={tab}
            type="button"
            aria-pressed={mode === tab}
            className={`${styles.tab} ${mode === tab ? styles.tabActive : ""}`}
            onClick={() => {
              setMode(tab);
              setError(null);
            }}
          >
            {tab === "sign-in" ? "Sign in" : "Create account"}
          </button>
        ))}
      </div>

      <form className={styles.form} onSubmit={submit} aria-describedby={error ? errorId : undefined}>
        {mode === "register" && (
          <TextField label="Full name" name="full_name" autoComplete="name" required maxLength={120} />
        )}
        <TextField label="Email" name="email" type="email" autoComplete="email" required maxLength={254} />
        {mode === "register" && (
          <TextField
            label="Mobile number (optional)"
            name="phone"
            type="tel"
            autoComplete="tel"
            inputMode="tel"
            pattern="\+?[0-9][0-9 \-]{6,18}"
            maxLength={20}
          />
        )}
        <TextField
          label="Password"
          name="password"
          type="password"
          autoComplete={mode === "sign-in" ? "current-password" : "new-password"}
          required
          minLength={mode === "register" ? 10 : undefined}
          maxLength={128}
        />
        {mode === "sign-in" && (
          <Link href="/account/forgot-password" className={styles.inlineLink}>
            Forgot your password?
          </Link>
        )}
        {error && (
          <p id={errorId} className={styles.error} role="alert">
            {error}
          </p>
        )}
        <Button type="submit" size="lg" fullWidth loading={busy}>
          {mode === "sign-in" ? "Sign in" : "Create account"}
        </Button>
      </form>
    </section>
  );
}

function Overview({
  user,
  onSignedOut,
  orderPolicy,
}: {
  user: CustomerProfile;
  onSignedOut: () => Promise<void>;
  orderPolicy: OrderPolicy | null;
}) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [profile, setProfile] = useState(user);
  const [tab, setTab] = useState<"orders" | "addresses" | "profile">("orders");
  const firstName = profile.full_name.split(" ")[0] || profile.full_name;

  async function handleSignOut() {
    setBusy(true);
    try {
      await signOut();
      await onSignedOut();
    } catch (error) {
      toast.show({ tone: "warning", title: "Couldn't sign you out", description: messageFor(error) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={styles.dashboard}>
      <section className={styles.header} aria-labelledby="account-title">
        <span className={styles.icon}>
          <UserRound aria-hidden="true" size={26} />
        </span>
        <div className={styles.headerText}>
          <h1 id="account-title" className={styles.title}>
            Hello, {firstName}
          </h1>
          <p className={styles.lede}>
            <Mail aria-hidden="true" size={14} /> {profile.email}
            {profile.phone && (
              <>
                {" · "}
                <Phone aria-hidden="true" size={14} /> {profile.phone}
              </>
            )}
          </p>
        </div>
        <div className={styles.links}>
          <ButtonLink href="/wishlist" variant="soft" size="sm" iconStart={<Heart aria-hidden="true" />}>
            Wishlist
          </ButtonLink>
          {profile.is_staff && (
            <ButtonLink href="/admin" variant="outline" size="sm" iconStart={<ShieldCheck aria-hidden="true" />}>
              Admin panel
            </ButtonLink>
          )}
          <Button variant="link" size="sm" onClick={() => void handleSignOut()} loading={busy} iconStart={<LogOut aria-hidden="true" size={16} />}>
            Sign out
          </Button>
        </div>
      </section>

      <div className={styles.tabs} role="group" aria-label="Account sections">
        {(
          [
            ["orders", "My orders"],
            ["addresses", "Addresses"],
            ["profile", "Profile & password"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            aria-pressed={tab === key}
            className={`${styles.tab} ${tab === key ? styles.tabActive : ""}`}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "orders" && <OrdersPanel policy={orderPolicy} />}
      {tab === "addresses" && <AddressesPanel />}
      {tab === "profile" && <ProfilePanel user={profile} onUpdated={setProfile} />}
    </div>
  );
}
