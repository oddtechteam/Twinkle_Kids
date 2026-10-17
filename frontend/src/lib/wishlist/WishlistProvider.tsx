"use client";

import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";

/**
 * Guest wishlist kept in localStorage (product slugs only — no personal data or credentials).
 * When customer accounts ship, sync these slugs to the account-backed wishlist API.
 */

const STORAGE_KEY = "tk:wishlist:v1";
const MAX_ITEMS = 60;

interface WishlistApi {
  slugs: string[];
  ready: boolean;
  has: (slug: string) => boolean;
  toggle: (slug: string) => boolean; // returns the new "saved" state
  remove: (slug: string) => void;
}

const WishlistContext = createContext<WishlistApi | null>(null);

function read(): string[] {
  try {
    const parsed: unknown = JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? "[]");
    return Array.isArray(parsed) ? parsed.filter((v): v is string => typeof v === "string") : [];
  } catch {
    return [];
  }
}

function write(slugs: string[]): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(slugs));
  } catch {
    // Storage can be unavailable (private mode); the wishlist still works for this visit.
  }
}

export function WishlistProvider({ children }: { children: ReactNode }) {
  const [slugs, setSlugs] = useState<string[]>([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setSlugs(read());
    setReady(true);
    const sync = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY) setSlugs(read());
    };
    window.addEventListener("storage", sync);
    return () => window.removeEventListener("storage", sync);
  }, []);

  const update = useCallback((next: string[]) => {
    setSlugs(next);
    write(next);
  }, []);

  const toggle = useCallback(
    (slug: string) => {
      const saved = slugs.includes(slug);
      update(saved ? slugs.filter((s) => s !== slug) : [slug, ...slugs].slice(0, MAX_ITEMS));
      return !saved;
    },
    [slugs, update],
  );

  const api = useMemo<WishlistApi>(
    () => ({
      slugs,
      ready,
      has: (slug) => slugs.includes(slug),
      toggle,
      remove: (slug) => update(slugs.filter((s) => s !== slug)),
    }),
    [slugs, ready, toggle, update],
  );

  return <WishlistContext.Provider value={api}>{children}</WishlistContext.Provider>;
}

export function useWishlist(): WishlistApi {
  const api = useContext(WishlistContext);
  if (!api) throw new Error("useWishlist must be used inside <WishlistProvider>");
  return api;
}
