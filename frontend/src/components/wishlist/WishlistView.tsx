"use client";

import { Heart } from "lucide-react";
import { useEffect, useState } from "react";

import { ProductGrid, ProductGridSkeleton } from "@/components/product/ProductGrid";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { ButtonLink } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/Feedback";
import { ApiError, apiFetch } from "@/lib/api/client";
import type { ProductDetail } from "@/lib/api/types";
import { type CardProduct, cardFromDetail } from "@/lib/catalog/adapters";
import { plural } from "@/lib/format";
import { useWishlist } from "@/lib/wishlist/WishlistProvider";
import styles from "./WishlistView.module.css";

type State = { status: "loading" } | { status: "ready"; items: CardProduct[] } | { status: "error" };

export function WishlistView() {
  const wishlist = useWishlist();
  const [state, setState] = useState<State>({ status: "loading" });
  const key = wishlist.slugs.join("|");

  useEffect(() => {
    if (!wishlist.ready) return;
    const slugs = key ? key.split("|") : [];
    if (slugs.length === 0) {
      setState({ status: "ready", items: [] });
      return;
    }
    const controller = new AbortController();
    (async () => {
      const results = await Promise.all(
        slugs.map(async (slug) => {
          try {
            return await apiFetch<ProductDetail>(`/products/${encodeURIComponent(slug)}`, {
              signal: controller.signal,
            });
          } catch (error) {
            // Products that were removed or unpublished simply drop out of the list.
            if (error instanceof ApiError && error.status === 404) return null;
            throw error;
          }
        }),
      ).catch(() => undefined);
      if (controller.signal.aborted) return;
      if (results === undefined) {
        setState({ status: "error" });
        return;
      }
      setState({
        status: "ready",
        items: results.filter((p): p is ProductDetail => p !== null).map(cardFromDetail),
      });
    })();
    return () => controller.abort();
  }, [key, wishlist.ready]);

  return (
    <div className={`container ${styles.page}`}>
      <Breadcrumbs items={[{ label: "Home", href: "/" }, { label: "Wishlist" }]} />
      <header className={styles.header}>
        <h1 className={styles.title}>Your wishlist</h1>
        {state.status === "ready" && state.items.length > 0 && (
          <p className={styles.count}>{plural(state.items.length, "saved style")}</p>
        )}
      </header>

      {state.status === "loading" && <ProductGridSkeleton count={4} />}
      {state.status === "error" && (
        <EmptyState
          tone="error"
          title="We couldn't load your wishlist"
          description="Your saved styles are safe on this device. Please try again in a moment."
        />
      )}
      {state.status === "ready" && state.items.length === 0 && (
        <EmptyState
          icon={<Heart aria-hidden="true" size={26} />}
          title="Nothing saved yet"
          description="Tap the heart on any style to save it here for later."
          action={<ButtonLink href="/shop">Discover styles</ButtonLink>}
        />
      )}
      {state.status === "ready" && state.items.length > 0 && <ProductGrid products={state.items} />}
      <p className={styles.note}>Your wishlist is saved on this device.</p>
    </div>
  );
}
