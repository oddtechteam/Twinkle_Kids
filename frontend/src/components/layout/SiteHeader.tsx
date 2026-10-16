import { Heart, Search, ShoppingBag, User } from "lucide-react";

import { Logo } from "@/components/brand/Logo";
import styles from "./SiteHeader.module.css";

const actions = [
  { label: "Search", Icon: Search },
  { label: "Wishlist", Icon: Heart },
  { label: "Account", Icon: User },
  { label: "Shopping bag", Icon: ShoppingBag },
] as const;

export function SiteHeader() {
  return (
    <header className={styles.header}>
      <div className={`container ${styles.inner}`}>
        <Logo />

        {/* Category navigation is rendered from the Catalog API in Phase 3. */}
        <nav aria-label="Main" className={styles.nav} />

        <ul className={styles.actions} aria-label="Shop actions">
          {actions.map(({ label, Icon }) => (
            <li key={label}>
              <button
                type="button"
                className={styles.iconButton}
                aria-label={label}
                aria-disabled="true"
                title={`${label} — coming soon`}
              >
                <Icon aria-hidden="true" strokeWidth={1.75} />
              </button>
            </li>
          ))}
        </ul>
      </div>
    </header>
  );
}
