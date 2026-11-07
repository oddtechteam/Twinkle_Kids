"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

/** Product and category pages live "inside" the shop for highlighting purposes. */
const SHOP_CHILDREN = /^\/(category|products)\//;

function trimPath(path: string): string {
  return path.length > 1 ? path.replace(/\/+$/, "") : path;
}

/**
 * How well `href` describes the current location (0 = not at all). Exact paths beat parent
 * paths, and every matching query parameter adds specificity, so on `/shop?sort=newest` "New In"
 * (`/shop?sort=newest`) outranks "Shop" (`/shop`), and on `/collections/festive-edit` the
 * occasion link outranks "Collections".
 */
function score(href: string, pathname: string, search: URLSearchParams, shopChildren: boolean): number {
  if (!href.startsWith("/") || href.startsWith("//")) return 0; // external links never match
  const url = new URL(href, "http://local");
  const path = trimPath(url.pathname);
  let base: number;
  if (pathname === path) base = 3;
  else if (path !== "/" && pathname.startsWith(`${path}/`)) base = 2;
  else if (shopChildren && path === "/shop" && SHOP_CHILDREN.test(pathname)) base = 1;
  else return 0;
  for (const [key, value] of url.searchParams) {
    if (search.get(key) !== value) return 0;
    base += 1;
  }
  return base;
}

/**
 * The most specific href for the current URL, or null. With `shopChildren`, product and
 * category pages fall back to a plain `/shop` link (main menu); without it they never do
 * (category strip, which has a link per category).
 */
export function activeHref(
  hrefs: string[],
  pathname: string,
  search: URLSearchParams,
  shopChildren = true,
): string | null {
  let best: string | null = null;
  let bestScore = 0;
  for (const href of hrefs) {
    const s = score(href, trimPath(pathname), search, shopChildren);
    if (s > bestScore) {
      best = href;
      bestScore = s;
    }
  }
  return best;
}

/**
 * Active link for a menu, with instant click feedback: the clicked link is shown as active
 * straight away and the real location takes over once navigation lands.
 * Needs a <Suspense> boundary above it (it reads search params).
 */
export function useActiveNav(hrefs: string[], { shopChildren = true }: { shopChildren?: boolean } = {}) {
  const pathname = usePathname();
  const search = useSearchParams();
  const location = `${pathname}?${search.toString()}`;
  const [pending, setPending] = useState<{ href: string; from: string } | null>(null);

  // Navigation landed (or was abandoned for another route): drop the optimistic state.
  useEffect(() => {
    setPending((current) => (current && current.from !== location ? null : current));
  }, [location]);

  const current = activeHref(hrefs, pathname, search, shopChildren);
  const active = pending && pending.from === location ? pending.href : current;

  const onNavigate = (href: string, event: { metaKey: boolean; ctrlKey: boolean; shiftKey: boolean; altKey: boolean; button: number }) => {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    if (href !== current) setPending({ href, from: location });
  };

  return { active, onNavigate };
}
